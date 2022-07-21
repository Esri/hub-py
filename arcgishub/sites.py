from arcgis.gis import GIS
from arcgis.features import FeatureLayer
from arcgis._impl.common._mixins import PropertyMap
from arcgis._impl.common._isd import InsensitiveDict
from datetime import datetime
from collections import OrderedDict
from urllib.parse import urlparse
import requests
import json
import os

def _lazy_property(fn):
    '''Decorator that makes a property lazy-evaluated.
    '''
    # http://stevenloria.com/lazy-evaluated-properties-in-python/
    attr_name = '_lazy_' + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)
    return _lazy_property

class Site(OrderedDict):
    """
    Represents a site within a Hub. A site is a container for 
    web accessible content.
    """
    
    def __init__(self, gis, siteItem):
        """
        Constructs an empty Site object
        """
        self.item = siteItem
        self._gis = gis
        try:
            self._sitedict = self.item.get_data()
            self.definition = PropertyMap(self._sitedict)
        except:
            self.definition = None
            
    def __repr__(self):
        return '<%s title:"%s" owner:%s>' % (
            type(self).__name__, 
            self.title, 
            self.owner
        )

    @property
    def itemid(self):
        """
        Returns the item id of the site item
        """
        return self.item.id
    
    @property
    def title(self):
        """
        Returns the title of the site item
        """
        return self.item.title
    
    @property
    def description(self):
        """
        Getter/Setter for the site description
        """
        return self.item.description
    
    @description.setter
    def description(self, value):
        self.item.description = value
        
    @property
    def owner(self):
        """
        Returns the owner of the site item
        """
        return self.item.owner

    @property
    def tags(self):
        """
        Returns the tags of the site item
        """
        return self.item.tags

    @tags.setter
    def tags(self, value):
        self.item.tags = value
    
    @property
    def url(self):
        """
        Returns the url of the site
        """
        return self.item.url

    @property
    def content_group_id(self):
        """
        Returns the groupId for the content group
        """
        try:
            return self.item.properties['contentGroupId']
        except:
            return self.initiative.content_group_id
    
    @property
    def collab_group_id(self):
        """
        Returns the groupId for the collaboration group
        """
        try:
            return self.item.properties['collaborationGroupId']
        except:
            return self.initiative.collab_group_id

    @property
    def catalog_groups(self):
        """
        Return Site catalog groups
        """
        return self.definition['catalog']['groups']

    @property
    def layout(self):
        """
        Return layout of a site
        """
        return InsensitiveDict(self.definition['values']['layout'])

    @property
    def theme(self):
        """
        Return theme of a site
        """
        return InsensitiveDict(self.definition['values']['theme'])

    @_lazy_property
    def pages(self):
        """
        The resource manager for an Initiative's indicators. 
        See :class:`~hub.sites.PageManager`.
        """
        return PageManager(self._gis, self)

    def add_content(self, items_list):
        """
        Adds a batch of items to the site content library.
        
        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        items_list                Required list. A list of Item or item ids to add to the initiative
        =====================     ====================================================================
        """
        #Fetch Initiative Collaboration group
        _collab_group = self._gis.groups.get(self.collab_group_id)
        #Fetch Content Group
        _content_group = self._gis.groups.get(self.content_group_id)
        #share items with groups
        return self._gis.content.share_items(items_list, groups=[_collab_group, _content_group])

    def add_catalog_group(self, group_id):
        """
        
        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        group_id            Group id to be added to site catalog
        ===============     ====================================================================
        """
        if group_id not in self.catalog_groups:
            self.definition['catalog']['groups'].append(group_id)
            self.item.update(item_properties={'text': self.definition})
            return self.catalog_groups

    def delete_catalog_group(self, group_id):
        """
        
        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        group_id            Group id to be added to site catalog
        ===============     ====================================================================
        """
        if group_id not in self.catalog_groups:
            raise Exception('Group is not a part of site catalog. Please check the group_id')
        self.definition['catalog']['groups'] = [group for group in self.catalog_groups if group!=group_id]
        self.item.update(item_properties={'text': self.definition})
        return self.catalog_groups

    def delete(self):
        """
        Deletes the site. If unable to delete, raises a RuntimeException.
        
        :return:
            A bool containing True (for success) or False (for failure). 
        
        .. code-block:: python
            
            USAGE EXAMPLE: Delete a site successfully
            
            site1 = myHub.sites.get('itemId12345')
            site1.delete()
            
            >> True
        """
        #Unlink site from pages. Delete page if not linked to other sites
        try:
            site_pages = self.pages.search()
            #If pages exist
            if len(site_pages) > 0:
                for page in site_pages:
                    #Unlink page (deletes if)
                    self.pages.unlink(page)
        #In case site definition is empty
        except:
            pass
        #Delete enterprise site
        if not self._gis._portal.is_arcgisonline:
             #Fetch Enterprise Site Collaboration group
            _collab_groupId = self.item.properties['collaborationGroupId']
            _collab_group = self._gis.groups.get(_collab_groupId)
            #Fetch Content Group
            _content_groupId = self.item.properties['contentGroupId']
            _content_group = self._gis.groups.get(_content_groupId)
            #Disable delete protection on groups and site
            _collab_group.protected = False
            _content_group.protected = False
            self.item.protect(enable=False)
            #Delete groups, site and initiative
            _collab_group.delete()
            _content_group.delete()
            return self.item.delete()
        #Deleting hub sites
        if self.item is not None:
            #Fetch site data
            _site_data = self.definition
            #Disable delete protection on site
            self.item.protect(enable=False)
            #Fetch siteId from domain entry
            _HEADERS = {
                'Content-Type': 'application/json', 
                'Authorization': self._gis._con.token, 
                'Referer': self._gis._con._referer
            }
            path = 'https://hub.arcgis.com/utilities/domains?siteId='+self.itemid
            _site_domain = requests.get(path, headers = _HEADERS)
            _siteId = _site_domain.json()[0]['id']
            #Delete domain entry
            _HEADERS = {
                'Content-Type': 'application/json', 
                'Authorization': self._gis._con.token, 
                'Referer': self._gis._con._referer
            }
            path = 'https://hub.arcgis.com/utilities/domains/'+_siteId
            _delete_domain = requests.delete(path, headers = _HEADERS)
            if _delete_domain.status_code==200:
                #Delete site item
                return self.item.delete()
            else:
                return _delete_domain.content

    def reassign_to(self, target_owner):
        """
        Allows the administrator to reassign the site object from one 
        user to another. 
        
        .. note::
            This will transfer ownership of all items (site, content) and groups to the new target_owner.
        
        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        target_owner              Required string. The new desired owner of the site.
        =====================     ====================================================================
        """
        #check if admin user is performing this action
        if 'admin' not in self._gis.users.me.role:
            return Exception("You do not have the administrator privileges to perform this action.")
        #check if core team is needed by checking the role of the target_owner
        if self._gis.users.get(target_owner).role=='org_admin':
            #check if the initiative comes with core team by checking owner's role
            if self._gis.users.get(self.owner).role=='org_admin':
                #fetch the core team for the initative 
                core_team = self._gis.groups.get(self.collab_group_id)
                #fetch the contents shared with this team
                core_team_content = core_team.content()
                #check if target_owner is part of core team, else add them to core team
                members = core_team.get_members()
                if target_owner not in members['admins'] or target_owner not in members['users']:
                    core_team.add_users(target_owner)
                #remove items from core team 
                self._gis.content.unshare_items(core_team_content, groups=[core_team])
                #reassign to target_owner
                for item in core_team_content:
                    item.reassign_to(target_owner)
                #fetch the items again since they have been reassigned
                new_content_list = []
                for item in core_team_content:
                    item_temp = self._gis.content.get(item.id)
                    new_content_list.append(item_temp)
                #share item back to the content group
                self._gis.content.share_items(new_content_list, groups=[core_team], allow_members_to_edit=True)
                #reassign core team to target owner
                core_team.reassign_to(target_owner)
            else:
                #create core team necessary for the initiative
                _collab_group_title = title + ' Core Team'
                _collab_group_dict = {
                    "title": _collab_group_title, 
                    "tags": ["Hub Group", "Hub Site Group", "Hub Core Team Group", "Hub Team Group"], 
                    "access":"org",
                    "capabilities":"updateitemcontrol",
                    "membershipAccess": "collaboration",
                    "snippet": "Members of this group can create, edit, and manage the site, pages, and other content related to hub-groups."
                }
                collab_group =  self._gis.groups.create_from_dict(_collab_group_dict)
                collab_group.protected = True
                self.collab_group_id = collab_group.id
        else:
            #just reassign the initiative and site items
            self.item.reassign_to(target_owner)
            site_pages = self.pages.search()
            #If pages exist
            if len(site_pages) > 0:
                for page in site_pages:
                    #Unlink page (deletes if)
                    page.item.reassign_to(target_owner) 
        #fetch content group
        content_team = self._gis.groups.get(self.content_group_id)
        #reassign to target_owner
        content_team.reassign_to(target_owner)
        return self._gis.content.get(self.itemid)


    def search(self, query=None, item_type=None):
        """ 
        Search and filter content for a site. 
        
        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        query                     Optional string. Filters items by presence of search query in title.
        ---------------------     --------------------------------------------------------------------
        item_type                 Optional list. Returns items of particular type.
        =====================     ====================================================================
        
        :return:
           List of items shared with this site.
        
        .. code-block:: python
            
            USAGE EXAMPLE: Succcessfully fetch items of item_type 'Web Mapping Application' 
            for particular query 'school' for site
            
            site1 = myHub.sites.get('itemId12345')
            site_apps = site1.search(query='school', item_type='Web Map')
            site_apps
            
            >> List of relevant items
        """
        groups = self.catalog_groups
        all_content = []
        for group_id in groups:
            group = self._gis.groups.get(group_id)
            try:
                all_content = all_content + group.content()
            except AttributeError:
                pass
        #eliminate duplicate items
        result = [i for n, i in enumerate(all_content) if i not in all_content[:n]]
        if query!=None:
            result = [item for item in result if query.lower() in item.title.lower()]
        if item_type!=None:
            result = [item for item in result if item.type==item_type]
        return result

    def update(self, site_properties=None, data=None, thumbnail=None, metadata=None):
        """ Updates the site.
        
        .. note::
            For site_properties, pass in arguments for only the properties you want to be updated.
            All other properties will be untouched.  For example, if you want to update only the
            site's description, then only provide the description argument in site_properties.
        
        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        site_properties           Required dictionary. See URL below for the keys and values.
        ---------------------     --------------------------------------------------------------------
        data                      Optional string. Either a path or URL to the data.
        ---------------------     --------------------------------------------------------------------
        thumbnail                 Optional string. Either a path or URL to a thumbnail image.
        ---------------------     --------------------------------------------------------------------
        metadata                  Optional string. Either a path or URL to the metadata.
        =====================     ====================================================================
        
        To find the list of applicable options for argument site_properties - 
        https://esri.github.io/arcgis-python-api/apidoc/html/arcgis.gis.toc.html#arcgis.gis.Item.update
        
        :return:
           A boolean indicating success (True) or failure (False).
        
        .. code-block:: python
            USAGE EXAMPLE: Update a site successfully
            
            site1 = myHub.sites.get('itemId12345')
            site1.update(site_properties={'description':'Description for site.'})
        
            >> True
        """
        if site_properties:
            _site_data = self.definition
            for key, value in site_properties.items():
                _site_data[key] = value
            return self.item.update(_site_data, data, thumbnail, metadata)

    
    def update_layout(self, layout):
        """ Updates the layout of the site. 

        .. note::
            This operation can only be performed by the owner of the site or by an org administrator.
        
        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        layout                    Required dictionary. The new layout dictionary to update to the site.
        =====================     ====================================================================
        
        :return:
           A boolean indicating success (True) or failure (False).
        
        .. code-block:: python
            
            USAGE EXAMPLE: Update a site successfully
            
            site1 = myHub.sites.get('itemId12345')
            site_layout = site1.layout
            site_layout.sections[0].rows[0].cards.pop(0)
            site1.update_layout(layout = site_layout)
            
            >> True
        """
        #Deleting the draft file for this site, if exists
        resources = self.item.resources.list()
        for resource in resources:
            if 'draft-' in resource['resource']:
                path = self._gis.url+'/sharing/rest/content/items/'+self.itemid+'/resources/'+resource['resource']+'?token='+self._gis._con.token
                self.item.resources.remove(file=path)
        #Update the data of the site
        self.definition['values']['layout'] = layout._json()
        return self.item.update(item_properties={'text': self.definition})

    def update_theme(self, theme):
        """ Updates the theme of the site. 

        .. note::
            This operation can only be performed by the owner of the site or by an org administrator.
        
        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        theme                     Required dictionary. The new theme dictionary to update to the site.
        =====================     ====================================================================
        
        :return:
           A boolean indicating success (True) or failure (False).
        
        .. code-block:: python
            
            USAGE EXAMPLE: Update a site successfully
            
            site1 = myHub.sites.get('itemId12345')
            site_theme = site1.theme
            site_theme.body.background = '#ffffff'
            site1.update_theme(theme = site_theme)
            
            >> True
        """
        #Deleting the draft file for this site, if exists
        resources = self.item.resources.list()
        for resource in resources:
            if 'draft-' in resource['resource']:
                path = self._gis.url+'/sharing/rest/content/items/'+self.itemid+'/resources/'+resource['resource']+'?token='+self._gis._con.token
                print(path)
                self.item.resources.remove(file=path)
        #Update the data of the site
        self.definition['values']['theme'] = theme._json()
        return self.item.update(item_properties={'text': self.definition})


class SiteManager(object):
    """
    Helper class for managing sites within a Hub. This class is not created by users directly. 
    An instance of this class, called 'sites', is available as a property of the Hub object. Users
    call methods on this 'sites' object to manipulate (add, get, search, etc) sites.
    """
    
    def __init__(self, hub, initiative=None):
        self._hub = hub
        self._gis = self._hub.gis
        self.initiative = initiative

    def _create_and_register_site(self, site, subdomain, site_data, content_group_id, collab_group_id):
        """
        Registers site as an app and Creates a domain entry for new site. 
        Updates data with necessary attributes for a new site.
        """

        basemap = {}

        if self._gis._portal.is_arcgisonline:

            #register site as an app
            _app_dict = site.register(app_type='browser', redirect_uris=[site.url])
            client_key = _app_dict['client_id']

            #Check for length of domain
            if len(subdomain + '-' + self._gis.properties['urlKey']) > 63:
                _num = 63 - len(self._gis.properties['urlKey'])
                raise ValueError('Requested url too long. Please enter a name shorter than %d characters' %_num)

            #Create domain entry for new site
            _HEADERS = {
                    'Content-Type': 'application/json', 
                    'Authorization': self._gis._con.token,
                    'Referer': self._gis._con._referer
                    }
            _body = {
                'hostname': subdomain + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com', 
                'siteId': site.id, 
                'siteTitle': site.title, 
                'clientKey': client_key, 
                'orgId': self._gis.properties.id, 
                'orgKey': self._gis.properties['urlKey'], 
                'orgTitle':self._gis.properties['name'],
                'sslOnly':True
                }
            path = 'https://hub.arcgis.com/utilities/domains'
            _new_domain = requests.post(path, headers = _HEADERS, data=json.dumps(_body))
            if _new_domain.status_code==200:
                _siteId = _new_domain.json()['id']
            else:
                return _new_domain
        else:
            #Check for length of domain
            if len(subdomain) > 63:
                raise ValueError('Requested url too long. Please enter a name shorter than 63 characters')


        #for group_id in group_ids:
        try:
            site_data['catalog']['groups'].append(content_group_id)
        except:
            site_data['values']['groups'].append(content_group_id)
            site_data['values']['uiVersion'] = "2.3"
        if self._gis._portal.is_arcgisonline:
            site_data['values']['theme']['globalNav'] = {}
            try:
                site_data['values']['theme']['globalNav'] = self._gis.properties['portalProperties']['sharedTheme']['header']
            except KeyError:
                raise KeyError("Hub does not exist or is inaccessible.")
        site_data['values']['title'] = site.title
        site_data['values']['layout']['header']['component']['settings']['title'] = site.title
        site_data['values']['collaborationGroupId'] = collab_group_id
        site_data['values']['subdomain'] = subdomain
        site_data['values']['defaultHostname'] = site.url
        site_data['values']['updatedBy'] = self._gis.users.me.username
        if self._gis._portal.is_arcgisonline:
            site_data['values']['siteId'] = _siteId
            site_data['values']['clientId'] = client_key
        else:
            site_data['values']['clientId'] = 'arcgisonline'
        #Add collaboration group to gallery card only if it exists in the usual spot
        try:
            site_data['values']['layout']['sections'][6]['rows'][1]['cards'][0]['component']['settings']['selectedGroups'][0]['id'] = collab_group_id
        except:
            pass
        #Link follow button to current initiative only if it exists in the usual spot
        if self._hub._hub_enabled:
            try:
                site_data['values']['layout']['sections'][8]['rows'][1]['cards'][0]['component']['settings']['initiativeId'] = self.initiative.itemid
            except:
                pass
        site_data['values']['map'] = self._gis.properties['defaultBasemap']
        site_data['values']['defaultExtent'] = self._gis.properties['defaultExtent']

        #site_data['values']['theme'] = self._gis.properties['portalProperties']['sharedTheme']
        return site_data

    def add(self, title):
        """ 
        Adds a new site.
        
        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        title               Required string.
        ===============     ====================================================================
        
        :return:
           The site if successfully added, None if unsuccessful.
        
        .. code-block:: python
            
            USAGE EXAMPLE: Add an open data site in Hub successfully 
            
            site1 = myHub.sites.add(title='My first site')
            site1.item

        .. code-block:: python
            
            USAGE EXAMPLE: Add an initiative site successfully 
            
            initiative_site = initiative1.sites.add(title=title)
            site1.item
        """

        siteId = None
        subdomain = title.replace(' ', '-').lower()
        #Check if initiative or site needs to be created for this gis
        if self._gis._portal.is_arcgisonline:
            if self._hub._hub_enabled:
                if self.initiative is None:
                    raise Exception("Sites are created as part of an Initiative for your Hub. Please add a new initiative to proceed.")

        #For sites in ArcGIS Online
        if self._gis._portal.is_arcgisonline:
            #Set item details
            item_type = "Hub Site Application"
            typekeywords = "Hub, hubSite, hubSolution, JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map, Registered App"
            tags = ["Hub Site"]
            description = "DO NOT DELETE OR MODIFY THIS ITEM. This item is managed by the ArcGIS Hub application. To make changes to this site, please visit https://hub.arcgis.com/admin/"
            
            #Domain manipulation
            domain = self._gis.url[:8] + subdomain + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com'
            _request_url = 'https://hub.arcgis.com/utilities/domains/'+domain[8:]
            _response = requests.get(_request_url)
        
            #Check if domain doesn't exist
            if _response.status_code==404:
                pass
            else:
            #If exists check if counter needs updating and update it
                try:
                    count = int(subdomain[-1])
                    count = count + 1
                    subdomain = subdomain[:-1] + str(count)
                except:
                    subdomain = subdomain + '1'
                domain = self._gis.url[:8] + subdomain + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com'
        
        #For Enterprise Sites
        else:
            item_type = "Site Application"
            typekeywords = "Hub, hubSite, hubSolution, hubsubdomain|" +subdomain+", JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map"
            tags = ["Enterprise Site"]
            description = "DO NOT DELETE OR MODIFY THIS ITEM. This item is managed by the ArcGIS Enterprise Sites application. To make changes to this site, please visit" + self._gis.url +"apps/sites/admin/"

            #Domain manipulation
            domain = 'https://' + self._gis.url[7:-5] + '/apps/sites/#/'+subdomain

            #Check if site subdomain exists
            if self._gis.content.search(query='typekeywords:hubsubdomain|'+subdomain+' AND title:'+title):
                print(self._gis.content.search(query='typekeywords:hubsubdomain|'+subdomain))
                raise ValueError("You already have a site that uses this subdomain. Please provide another title.")

        #setting item properties based on type of site
        if self._gis._portal.is_arcgisonline and self._hub._hub_enabled:
            #Hub Premium Site
            #if self._hub._hub_enabled:
            content_group_id = self.initiative.content_group_id
            collab_group_id = self.initiative.collab_group_id
            _item_dict = {
                "type":item_type, 
                "typekeywords":typekeywords,
                "tags": tags,
                "title":title,
                "description":description, 
                "culture": self._gis.properties.user.culture,
                "properties": {
                    'hasSeenGlobalNav': True, 
                    'createdFrom': 'defaultInitiativeSiteTemplate', 
                    'schemaVersion': 1.5, 
                    'contentGroupId': content_group_id, 
                    'followersGroupId': self.initiative.followers_group_id, 
                    'parentInitiativeId': self.initiative.itemid, 
                    'children': []
                }, 
                "url":domain
            }
            if collab_group_id:
                collab_group = self._gis.groups.get(collab_group_id)
                _item_dict["properties"]["collaborationGroupId"] = collab_group_id
            _datafile = 'init-sites-data.json'
            
        
        #Non Hub Premium Sites
        else:
            #Checking if it is a Hub Basic site
            if self._gis._portal.is_arcgisonline:
                content_group_id = self.initiative.content_group_id
                collab_group_id = self.initiative.collab_group_id
            else:
                #Defining content, collaboration groups for Enterprise Sites
                _content_group_dict = {
                    "title": subdomain + ' Content', 
                    "tags": ["Hub Group", "Hub Content Group", "Hub Site Group", "Hub Initiative Group"], 
                    "access":"public"
                }
                _collab_group_dict = {
                    "title": subdomain + ' Core Team', 
                    "tags": ["Hub Group", "Hub Initiative Group", "Hub Site Group", "Hub Core Team Group", "Hub Team Group"], 
                    "access":"org",
                    "capabilities":"updateitemcontrol",
                    "membershipAccess": "collaboration",
                    "snippet": "Members of this group can create, edit, and manage the site, pages, and other content related to hub-groups."
                }
                #Create groups
                content_group =  self._gis.groups.create_from_dict(_content_group_dict)
                content_group_id = content_group.id
                #Create collaboration group if necessary privileges exist
                if self._gis.users.me.role=='org_admin':
                    collab_group =  self._gis.groups.create_from_dict(_collab_group_dict)
                    collab_group.protected = True
                    collab_group_id = collab_group.id
                #Protect groups from accidental deletion
                content_group.protected = True
            _item_dict = {
                "type": item_type, 
                "typekeywords":typekeywords, 
                "tags": tags, 
                "title":title, 
                "description":description,
                "properties": {
                    'hasSeenGlobalNav': True, 
                    'createdFrom': 'solutionPortalSiteTemplate', 
                    'schemaVersion': 1.3, 
                    'contentGroupId': content_group_id,
                    'children': []
                }, 
                "url":domain
            }
            if collab_group_id is not None:
                _item_dict["properties"]["collaborationGroupId"] = collab_group.id
            _datafile = 'sites-data.json'

        #Create site item, share with group
        site = self._gis.content.add(_item_dict, owner=self._gis.users.me.username)

        #Share with necessary group if group exists
        try:
            site.share(groups=[collab_group])
        except:
            pass

        #protect site from accidental deletion
        site.protect(enable=True)

        #Setting data for site
        data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '_store/'+_datafile))
        
        with open(data_path) as f:
            _site_data = json.load(f)

        #Register site and update its data
        _data = self._create_and_register_site(site, subdomain, _site_data, content_group_id, collab_group_id)
        _data = json.dumps(_data)
        site.update(item_properties={'text': _data, 'url': domain})
        return Site(self._gis, site)

    def clone(self, site, pages=True, title=None):
        """
        Clone allows for the creation of a site that is derived from the current site.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        site                Required Site object of site to be cloned.
        ---------------     --------------------------------------------------------------------
        pages               Optional Boolean. Decides if pages will be copied. Default is True.
        ---------------     --------------------------------------------------------------------
        title               Optional String.
        ===============     ====================================================================
        
        :return:
           Site.
        """
        collab_group_id = None
        from datetime import timezone
        now = datetime.now(timezone.utc)
        #Checking if item of correct type has been passed 
        if 'hubSite' not in site.item.typeKeywords:
            raise Exception("Incorrect item type. Site item needed for cloning.")
        #New title
        if title is None:
            title = site.title + "-copy-%s" % int(now.timestamp() * 1000)
        if self.initiative is None:
            if self._hub._hub_enabled:
                return self._hub.initiatives.add(title, site=site)
        subdomain = title.replace(' ', '-').lower()
        if self._gis._portal.is_arcgisonline:
            item_type = "Hub Site Application"
            typekeywords = "Hub, hubSite, hubSolution, JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map, Registered App"
            description = "DO NOT DELETE OR MODIFY THIS ITEM. This item is managed by the ArcGIS Hub application. To make changes to this site, please visit https://hub.arcgis.com/admin/"
            domain = self._gis.url[:8] + subdomain + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com'
    
        else:
            item_type = "Site Application"
            typekeywords = "Hub, hubSite, hubSolution, hubsubdomain|" +subdomain+", JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map"
            domain = 'https://' + self._gis.url[7:-5] + '/apps/sites/#/'+subdomain
        _site_properties = {
                        "type":item_type, 
                        "typekeywords":typekeywords, 
                        "tags": ["Hub Site"], 
                        "title":title, 
                        "url":domain
        }
        #Updating properties, groups for Hub sites
        if self.initiative is not None:
            content_group_id = self.initiative.content_group_id
            collab_group_id = self.initiative.collab_group_id
            _site_properties["properties"] = {
                'hasSeenGlobalNav': True, 
                'createdFrom': 'defaultInitiativeSiteTemplate', 
                'schemaVersion': 1.5, 
                'contentGroupId': content_group_id,
                'parentInitiativeId': self.initiative.itemid, 
                'children': []
            }
            if self._hub._hub_enabled:
                _site_properties["properties"]['followersGroupId'] = self.initiative.followers_group_id
            if collab_group_id:
                collab_group = self._gis.groups.get(collab_group_id)
                _site_properties["properties"]['collaborationGroupId'] = collab_group_id
        else:
            #Defining content, collaboration groups for Enterprise Sites
            _content_group_dict = {
                "title": subdomain + ' Content', 
                "tags": ["Hub Group", "Hub Content Group", "Hub Site Group", "Hub Initiative Group"], 
                "access":"public"
            }
            _collab_group_dict = {
                "title": subdomain + ' Core Team', 
                "tags": ["Hub Group", "Hub Initiative Group", "Hub Site Group", "Hub Core Team Group", "Hub Team Group"], 
                "access":"org",
                "capabilities":"updateitemcontrol",
                "membershipAccess": "collaboration",
                "snippet": "Members of this group can create, edit, and manage the site, pages, and other content related to hub-groups."
            }
            #Create content group
            content_group =  self._gis.groups.create_from_dict(_content_group_dict)
            content_group_id = content_group.id
            #Protect groups from accidental deletion
            content_group.protected = True
            _site_properties["properties"] = {
                                            'hasSeenGlobalNav': True, 
                                            'createdFrom': 'solutionPortalSiteTemplate', 
                                            'schemaVersion': 1.5,  
                                            'contentGroupId': content_group_id
                                            }
            #Create collaboration group if privilege exists
            if self._gis.users.me.role=='org_admin':
                collab_group =  self._gis.groups.create_from_dict(_collab_group_dict)
                collab_group_id = collab_group.id
                collab_group.protected = True
                _site_properties["properties"]["collaborationGroupId"] = collab_group_id
            
        #Create site item, share with group
        new_item = self._gis.content.add(_site_properties, owner=self._gis.users.me.username)

        #Share with necessary group
        try:
            new_item.share(groups=[collab_group])
        except:
            pass

        #Register new site and update its data
        _data = self._create_and_register_site(new_item, subdomain, site.definition, content_group_id, collab_group_id)

        new_item.update(item_properties={'text': _data, 'url': domain})
        new_site = Site(self._gis, new_item)

        #Pages of the site
        site_pages = site.pages.search()
        #If pages exist
        if len(site_pages) > 0:
            #Check the value of param
            if pages:
                for page in site_pages:
                    try:
                        new_site.pages.unlink(page)
                    except:
                        pass
                    new_site.pages.clone(page)

        return new_site

    def get(self, site_id):
        """ Returns the site object for the specified site_id.
        
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        site_id                    Required string. The site itemid.
        =======================    =============================================================
        
        :return:
            The site object if the item is found, None if the item is not found.
        
        .. code-block:: python
        
            USAGE EXAMPLE: Fetch a site successfully
        
            site1 = myHub.sites.get('itemId12345')
            site1.item
        """
        siteItem = self._gis.content.get(site_id)
        if 'hubSite' in siteItem.typeKeywords:
            return Site(self._gis, siteItem)
        else:
            raise TypeError("Item is not a valid site or is inaccessible.")

    def get_by_domain(self, domain_url):
        """ Returns the site object for the specified domain url.
        
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        domain_url                 Required string. The site url.
        =======================    =============================================================
        
        :return:
            The site object if the item is found, None if the item is not found.
        
        .. note:: 
            You may only fetch sites by domain local to your environment.
            E.g. If your Hub instance is an ArcGIS Online instance, then you can 
            fetch ArcGIS Online sites by url, and if you have signed into an ArcGIS
            Enterprise Instance, only sites on premise will be available.
        
        .. code-block:: python
            
            USAGE EXAMPLE: Fetch a site successfully
            
            site1 = myHub.sites.get_by_domain('opendata.dc.gov')
            site1.item
        """
        #Check if Hub(GIS) is an ArcGIS Online instance
        if self._gis._portal.is_arcgisonline:
            if 'http' in domain_url:
                domain_url = urlparse(domain_url).netloc
            path = 'https://hub.arcgis.com/utilities/domains/'+domain_url
            #fetch site itemid from domain service
            _HEADERS = {
                'Content-Type': 'application/json', 
                'Authorization': self._gis._con.token, 
                'Referer': self._gis._con._referer
            }
            _site_domain = requests.get(path, headers = _HEADERS)
            try:
                siteId = _site_domain.json()['siteId']
            except KeyError:
                raise Exception("Domain record not found. Please check your domain_url.")
            return self.get(siteId)
        #For ArcGIS Enterprise
        else:
            subdomain = domain_url.split("#/",1)[1]
            _query = 'hubsubdomain|'+subdomain
            items = self._gis.content.search(query='typekeywords:hubSite,'+_query, max_items=5000)
            #Return searched sites
            for item in items:
                sitelist.append(Site(self._gis, item))
            return sitelist
            
    def search(self, title=None, owner=None, created=None, modified=None, tags=None):
        """ 
        Searches for sites.
        
        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        title               Optional string. Return sites with provided string in title.
        ---------------     --------------------------------------------------------------------
        owner               Optional string. Return sites owned by a username.
        ---------------     --------------------------------------------------------------------
        created             Optional string. Date the site was created.
                            Shown in milliseconds since UNIX epoch.
        ---------------     --------------------------------------------------------------------
        modified            Optional string. Date the site was last modified.
                            Shown in milliseconds since UNIX epoch
        ---------------     --------------------------------------------------------------------
        tags                Optional string. User-defined tags that describe the site.
        ===============     ====================================================================
        
        :return:
           A list of matching sites.
        """

        sitelist = []
        
        if self.initiative is not None:
            _site_id = self.initiative.site_id
            return self.get(_site_id)

        #Build search query
        query = 'typekeywords:hubSite'
        if title!=None:
            query += ' AND title:'+title
        if owner!=None:
            query += ' AND owner:'+owner
        if created!=None:
            query += ' AND created:'+created
        if modified!=None:
            query += ' AND modified:'+modified
        if tags!=None:
            query += ' AND tags:'+tags
        
        #Search
        items = self._gis.content.search(query=query, max_items=5000)
        
        #Return searched sites
        for item in items:
            sitelist.append(Site(self._gis, item))
        return sitelist

class Page(OrderedDict):
    """
    Represents a page belonging to a site in Hub. A Page is a layout of 
    content that can be rendered within the context of a Site
    """
    
    def __init__(self, gis, pageItem):
        """
        Constructs an empty Page object
        """
        self.item = pageItem
        self._gis = gis
        try:
            self._pagedict = self.item.get_data()
            pmap = PropertyMap(self._pagedict)
            self.definition = pmap
        except:
            self.definition = None
            
    def __repr__(self):
        return '<%s title:"%s" owner:%s>' % (
            type(self).__name__, 
            self.item.title, 
            self.item.owner
        )
    
    @property
    def itemid(self):
        """
        Returns the item id of the page item
        """
        return self.item.id
    
    @property
    def title(self):
        """
        Returns the title of the page item
        """
        return self.item.title
    
    @property
    def description(self):
        """
        Getter/Setter for the page description
        """
        return self.item.description
    
    @description.setter
    def description(self, value):
        self.item.description = value

    @property
    def layout(self):
        """
        Return layout of a page
        """
        return InsensitiveDict(self.definition['values']['layout'])
        
    @property
    def owner(self):
        """
        Returns the owner of the page item
        """
        return self.item.owner

    @property
    def tags(self):
        """
        Returns the tags of the page item
        """
        return self.item.tags

    @tags.setter
    def tags(self, value):
        self.item.tags = value
    
    @property
    def slug(self):
        """
        Returns the page slug
        """
        return self.title.replace(' ', '-').lower()

    def update(self, page_properties=None, slug=None, data=None, thumbnail=None, metadata=None):
        """ Updates the page.
        
        .. note::
            
            For page_properties, pass in arguments for only the properties you want to be updated.
            All other properties will be untouched.  For example, if you want to update only the
            page's description, then only provide the description argument in page_properties.
        
        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        page_properties           Required dictionary. See URL below for the keys and values.
        ---------------------     --------------------------------------------------------------------
        data                      Optional string. Either a path or URL to the data.
        ---------------------     --------------------------------------------------------------------
        thumbnail                 Optional string. Either a path or URL to a thumbnail image.
        ---------------------     --------------------------------------------------------------------
        metadata                  Optional string. Either a path or URL to the metadata.
        =====================     ====================================================================
        
        To find the list of applicable options for argument page_properties - 
        https://esri.github.io/arcgis-python-api/apidoc/html/arcgis.gis.toc.html#arcgis.gis.Item.update
        
        :return:
           A boolean indicating success (True) or failure (False).
        
        .. code-block:: python
            
            USAGE EXAMPLE: Update a page successfully
            
            page1 = mySite.pages.get('itemId12345')
            page1.update(page_properties={'description':'Description for page.'})
            
            >> True
        """
        _page_data = self.definition
        if page_properties:
            for key, value in page_properties.items():
                _page_data[key] = value
        if slug:
            #Fetch all the sites this page is connected to
            linked_sites = self.definition['values']['sites']
            for item in linked_sites:
                #Update the title and slug on the parent sites
                site_item = self._gis.content.get(item['id'])
                site = Site(self._gis, site_item)
                site.definition['values']['pages'] = [p for p in site.definition['values']['pages'] if p['id']!=self.itemid]
                _renamed_page = {}
                _renamed_page['id'] = self.itemid
                _renamed_page['title'] = slug
                _renamed_page['slug'] = slug
                site.definition['values']['pages'].append(_renamed_page)
                site.item.update(item_properties={'text': site.definition})
            #Update the slug on the page
            _page_data['title'] = slug
        return self.item.update(_page_data, data, thumbnail, metadata)

    def update_layout(self, layout):
        """ Updates the layout of the page.
        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        layout                    Required dictionary. The new layout dictionary to update to the page.
        =====================     ====================================================================
        :return:
           A boolean indicating success (True) or failure (False).
        .. code-block:: python
            USAGE EXAMPLE: Update a site successfully
            page1 = myHub.pages.get('itemId12345')
            page_layout = page1.layout
            page_layout.sections[0].rows[0].cards.pop(0)
            page1.update_layout(layout = page_layout)
            >> True
        """
        #Calling the update layout method for site with this page object
        Site.update_layout(self, layout)
 
    def delete(self):
        """
        Deletes the page. If unable to delete, raises a RuntimeException.
        
        :return:
            A bool containing True (for success) or False (for failure). 
        
        .. code-block:: python
        
            USAGE EXAMPLE: Delete a page successfully
        
            page1 = myHub.pages.get('itemId12345')
            page1.delete()
        
            >> True
        """
        #Unlink sites
        linked_sites = self.definition['values']['sites']
        for item in linked_sites:
            site_item = self._gis.content.get(item['id'])
            site = Site(self._gis, site_item)
            site.definition['values']['pages'] = [p for p in site.definition['values']['pages'] if p['id']!=self.itemid]
            site.item.update(item_properties={'text': site.definition})
        #Remove delete protection on page
        self.item.protect(enable=False)
        #Delete page item
        self.item.delete()

class PageManager(object):
    """
    Helper class for managing pages within a Hub. This class is not created by users directly. 
    An instance of this class, called 'pages', is available as a property of the Site object. Users
    call methods on this 'pages' object to manipulate (add, get, search, etc) pages for a site.
    """
    
    def __init__(self, gis, site=None):
        #self._hub = hub
        #self._gis = self._hub.gis
        self._gis = gis
        self._site = site

    def add(self, title, site=None):
        """ 
        Returns the pages linked to the specific site.
        
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        title                      Required string. The title of the new page.
        -----------------------    -------------------------------------------------------------
        site                       Optional string. The site object to add the page to.
        =======================    =============================================================
        
        :return:
           The page if successfully added, None if unsuccessful.
        
        .. code-block:: python
        
            USAGE EXAMPLE: Add a page to a site successfully 
        
            page1 = mySite.pages.add(title='My first page')
            page1.item

        .. code-block:: python
        
            USAGE EXAMPLE: Add a page successfully 
        
            page2 = myHub.pages.add(title='My second page', site=mySite)
            page2.item
        """
        #If site object is not provided
        if site is None:
            if self._site is None:
                raise Exception('Site object needed for adding page')
        #If called from a specified site
        if self._site is not None:
            site = self._site
        #Fetch site group
        collab_group = self._gis.groups.get(site.collab_group_id)
    
        #For pages in ArcGIS Online
        if self._gis._portal.is_arcgisonline:
            #Set item details
            item_type = "Hub Page"
            typekeywords = "Hub, hubPage, JavaScript, Map, Mapping Site, Online Map, OpenData, selfConfigured, Web Map"
            description = "DO NOT DELETE OR MODIFY THIS ITEM. This item is managed by the ArcGIS Hub application. To make changes to this site, please visit https://hub.arcgis.com/overview/edit"
            image_card_url = 'https://cloud.githubusercontent.com/assets/7389593/20107607/1d2c3844-a5a7-11e6-9ec0-9e389033ccd8.jpg'
        #For Enterprise Sites
        else:
            item_type = "Site Page"
            typekeywords = "Hub, hubPage, JavaScript, Map, Mapping Site, Online Map, OpenData, selfConfigured, Web Map"
            description = "DO NOT DELETE OR MODIFY THIS ITEM. This item is managed by the ArcGIS Enterprise Sites application. To make changes to this site, please visit" + self._gis.url +"/apps/sites/#/home/overview/edit/"
            image_card_url = self._gis.url +'/apps/sites/images/placeholders/page-editor-card-image-placeholder.jpg'
        #Create page item
        _item_dict = {
                    "title":title,
                    "type": item_type,
                    "typeKeywords": typekeywords,
                    "description": description,
                    "culture": self._gis.properties.user.culture
                    }
        item =  self._gis.content.add(_item_dict, owner=self._gis.users.me.username)
        
        #share page with content and core team groups
        item.share(groups=[collab_group])

        #protect page from accidental deletion
        item.protect(enable=True)

        #Fetching page data
        data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '_store/pages-data.json'))
        with open(data_path) as f:
            _page_data = json.load(f)

        #Updating page data
        _page_data['values']['layout']['sections'][1]['rows'][0]['cards'][0]['component']['settings']['src'] = image_card_url
        _page_data['values']['updatedBy'] = self._gis.users.me.username
        _data = json.dumps(_page_data)
        item.update(item_properties={'text': _data})
        page = Page(self._gis, item)
        #Link page to site
        status = site.pages.link(page)
        if status:
            return page

    def clone(self, page, site=None):
        """
        Clone allows for the creation of a page that is derived from the current page.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        page                Required Page object of page to be cloned.
        ---------------     --------------------------------------------------------------------
        site                Optional Site object.
        ===============     ====================================================================
        
        :return:
           Page.
        """
        from datetime import timezone
        now = datetime.now(timezone.utc)
        #New title
        title = page.title + "-copy-%s" % int(now.timestamp() * 1000)
        #Checking if item of correct type has been passed 
        if 'hubPage' not in page.item.typeKeywords:
            raise Exception("Incorrect item type. Page item needed for cloning.")
        #If site object is not provided
        if site is None:
            if self._site is None:
                raise Exception('Site object needed for cloning page')
        #If called from a specified site
        if self._site is not None:
            site = self._site
        #Create new page within site
        _cloned_page = site.pages.add(title)
        #Copy the page layout
        _cloned_page.definition['values']['layout'] = page.definition['values']['layout']
        #_data = json.dumps(_cloned_page.definition)
        _cloned_page.item.update(item_properties={'text': _cloned_page.definition})
        return Page(self._gis, _cloned_page.item)
        
    def get(self, page_id):
        """ 
        Returns the page object for the specified page_id.
        
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        page_id                    Required string. The page itemid.
        =======================    =============================================================
        
        :return:
            The page object if the item is found, None if the item is not found.
        
        .. code-block:: python
        
            USAGE EXAMPLE: Fetch a page successfully
            page1 = myHub.pages.get('itemId12345')
            page1.item
        """
        pageItem = self._gis.content.get(page_id)
        if 'hubPage' in pageItem.typeKeywords:
            return Page(self._gis, pageItem)
        else:
            raise TypeError("Item is not a valid page or is inaccessible.")

    def link(self, page, site=None, slug=None):
        """ 
        Links the page to the specific site.
        
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        page                       Required string. The page object to link.
        -----------------------    -------------------------------------------------------------
        site                       Optional string. The site object to link page to.
        -----------------------    -------------------------------------------------------------
        slug                       Optional string. The slug reference of the page in this site.
        =======================    =============================================================
        
        :return:
            A bool containing True (for success) or False (for failure).
        
        .. code-block:: python
        
            USAGE EXAMPLE: Link a page successfully for specific site
            mySite.pages.link(page_id='itemId12345')
        
            >> True
            
        .. code-block:: python
        
            USAGE EXAMPLE: Link a page successfully for site object passed as param
            myHub.pages.link(page_id='itemId12345', site=mySite)
        
            >> True
        """
        _new_page = {}
        _new_site = {}
        #Checking if item of correct type has been passed 
        if 'hubPage' not in page.item.typeKeywords:
            raise Exception("Incorrect item type. Page item needed for cloning.")
        #If site object is not provided
        if site is None:
            if self._site is None:
                raise Exception('Site object needed for linking page')
        #If called from a specified site
        if self._site is not None:
            site = self._site
        #Create new page dictionary
        _site_data = site.definition    
        _new_page['id'] = page.itemid
        _new_page['title'] = page.title
        if slug is not None:
            _new_page['slug'] = slug.replace(' ', '-').lower()
        else:
            _new_page['slug'] = page.slug
        _site_data['values']['pages'].append(_new_page)
        #Create new site dictionary
        _page_data = page.definition    
        _new_site['id'] = site.itemid
        _new_site['title'] = site.title
        _page_data['values']['sites'].append(_new_site)
        #Update page and site data with new linking
        page.item.update(item_properties={'text': _page_data})
        return site.item.update(item_properties={'text': _site_data})

    def unlink(self, page, site=None):
        """ 
        Unlinks the page from the specific site.
        
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        page                       Required string. The page object to unlink.
        -----------------------    -------------------------------------------------------------
        site                       Optional string. The site object to unlink page from.
        =======================    =============================================================
        
        :return:
            A bool containing True (for success) or False (for failure).
        
        .. code-block:: python
        
            USAGE EXAMPLE: Unlink a page successfully from specific site
        
            mySite.pages.unlink(page_id='itemId12345')
        
            >> True
            
        .. code-block:: python
        
            USAGE EXAMPLE: Unlink a page successfully from site object passed as param
        
            myHub.pages.unlink(page_id='itemId12345', site=mySite)
        
            >> True
        """
        #If site object is not provided
        if site is None:
            if self._site is None:
                raise Exception('Site object needed for unlinking page')
        #Checking if item of correct type has been passed 
        if 'hubPage' not in page.item.typeKeywords:
            raise Exception("Incorrect item type. Page item needed for cloning.")
        #If called from a specified site
        if self._site is not None:
            site = self._site
        #Update site and pages with the unlinking
        _site_data = site.definition  
        _page_data = page.definition  
        _site_data['values']['pages'] = [p for p in _site_data['values']['pages'] if p['id']!=page.itemid]
        _page_data['values']['sites'] = [s for s in _page_data['values']['sites'] if s['id']!=site.itemid]
        #Delete page if it has no other site linkage
        if len(_page_data['values']['sites'])==0:
            page.delete()
        #Update page data to reflect unlinking
        else:
            page.item.update(item_properties={'text': _page_data})
        #Update site data to reflect unlinking
        return site.item.update(item_properties={'text': _site_data})

    def search(self, title=None, owner=None, created=None, modified=None, tags=None):
        """ 
        Searches for pages.
        
        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        title               Optional string. Return pages with provided string in title.
        ---------------     --------------------------------------------------------------------
        owner               Optional string. Return pages owned by a username.
        ---------------     --------------------------------------------------------------------
        created             Optional string. Date the page was created.
                            Shown in milliseconds since UNIX epoch.
        ---------------     --------------------------------------------------------------------
        modified            Optional string. Date the page was last modified.
                            Shown in milliseconds since UNIX epoch
        ---------------     --------------------------------------------------------------------
        tags                Optional string. User-defined tags that describe the page.
        ===============     ====================================================================
        
        :return:
           A list of matching pages.
        """

        pagelist = []

        if self._site is not None:
            pages = self._site.definition['values']['pages']
            items = [self._gis.content.get(page['id']) for page in pages]
        #Build search query
        else:
            query = 'typekeywords:hubPage'
            if title!=None:
                query += ' AND title:'+title
            if owner!=None:
                query += ' AND owner:'+owner
            if created!=None:
                query += ' AND created:'+created
            if modified!=None:
                query += ' AND modified:'+modified
            if tags!=None:
                query += ' AND tags:'+tags
        
            #Search
            items = self._gis.content.search(query=query, max_items=5000)
        
        #Return searched pages
        for item in items:
            pagelist.append(Page(self._gis, item))
        return pagelist