from arcgis.gis import GIS
from arcgis.features import FeatureLayer
from arcgis._impl.common._mixins import PropertyMap
from datetime import datetime
import collections
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

class Site(collections.OrderedDict):
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
            pmap = PropertyMap(self._sitedict)
            self.definition = pmap
        except:
            self.definition = None
            
    def __repr__(self):
        return '<%s title:"%s" owner:%s>' % (type(self).__name__, self.title, self.owner)
    
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
    def catalog_groups(self):
        """
        Return Site catalog groups
        """
        return self.definition['catalog']['groups']

    def add_card(self, section, card_data):
        """
        Add a card to the existing site.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        section             Required integer. Index of particular section.
        ---------------     --------------------------------------------------------------------
        card_data           Required list. Card data to be added.
        ===============     ====================================================================
        :return:
           A boolean indicating success (True) or failure (False).
        """
        new_row = {'cards':card_data}
        self.definition['values']['layout']['sections'][section]['rows'].append(new_row)
        self.item.update(item_properties={'text': self.definition})

    def clone(self, title=None, destination_hub=None):
        """
        Clone allows for the creation of a site that is derived from the current site.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        site                Required Site object of site to be cloned.
        ---------------     --------------------------------------------------------------------
        title               Optional String.
        ===============     ====================================================================
        :return:
           Site.
        """
        if title is None:
            title = self.title + "-copy-%s" % int(now.timestamp() * 1000)
        if destination_hub is None:
            destination_hub = self._hub
        if self._hub._hub_enabled:
            raise Exception("Please clone the initiative object based on your hub.")
        else:
            if destination_hub._hub_enabled:
                #new initiative
                new_initiative = destination_hub.initiatives.add(title=title, site=self)
                return new_initiative
            else:
                #new site
                print('Create new site')
            

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
        #Delete enterprise site
        if not self._gis._portal.is_arcgisonline:
            return self.item.delete()
        #Deleting hub sites
        if self.item is not None:
            #Fetch site data
            _site_data = self.definition
            #Disable delete protection on site
            self.item.protect(enable=False)
            #Fetch siteId from domain entry
            _HEADERS = {'Content-Type': 'application/json', 'Authorization': self._gis._con.token}
            path = 'https://hub.arcgis.com/utilities/domains?siteId='+self.itemid
            _site_domain = requests.get(path, headers = _HEADERS)
            _siteId = _site_domain.json()[0]['id']
            #Delete domain entry
            _HEADERS = {'Content-Type': 'application/json', 'Authorization': self._gis._con.token}
            path = 'https://hub.arcgis.com/utilities/domains/'+_siteId
            _delete_domain = requests.delete(path, headers = _HEADERS)
            if _delete_domain.status_code==200:
                #Delete site item
                return self.item.delete()
            else:
                return _delete_domain.content

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
 
class SiteManager(object):
    """
    Helper class for managing sites within a Hub. This class is not created by users directly. 
    An instance of this class, called 'sites', is available as a property of the Hub object. Users
    call methods on this 'sites' object to manipulate (add, get, search, etc) sites.
    """
    
    def __init__(self, hub, initiative=None):
        self._hub= hub
        self._gis = self._hub.gis
        self._initiative = initiative

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
                    'Authorization': self._gis._con.token
                    }
            _body = {
                'hostname': subdomain + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com', 
                'siteId': site.id, 
                'siteTitle': site.title, 
                'clientKey': client_key, 
                'orgId': self._gis.properties.id, 
                'orgKey': self._gis.properties['urlKey'], 
                'orgTitle':self._gis.properties['name']
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
            site1 = myHub.sites.add(title='My first site', domain='first-site', group_id='4ef..')
            site1.item

        .. code-block:: python
            USAGE EXAMPLE: Add an initiative site successfully 
            initiative_site = initiative1.sites.add(title=title, domain=title, group_id='4ef..')
            site1.item
        """

        siteId = None
        subdomain = title.replace(' ', '-').lower()
        #Check if initiative or site needs to be created for this gis
        if self._gis._portal.is_arcgisonline:
            if self._hub._hub_enabled:
                if self._initiative is None:
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
            tags = ["Hub Site"]
            description = "DO NOT DELETE OR MODIFY THIS ITEM. This item is managed by the ArcGIS Enterprise Sites application. To make changes to this site, please visit" + self._gis.url +"apps/sites/admin/"

            #Domain manipulation
            domain = 'https://' + self._gis.url[7:] + '/apps/sites/#/'+subdomain

            #Check if site subdomain exists
            if self._gis.content.search(query='typekeywords:hubsubdomain|'+subdomain+' AND title:'+title):
                print(self._gis.content.search(query='typekeywords:hubsubdomain|'+subdomain))
                raise ValueError("You already have a site that uses this subdomain. Please provide another title.")

        #setting item properties based on type of site
        #Hub Premium Site
        if self._hub._hub_enabled:
            _item_dict = {
                        "type":item_type, 
                        "typekeywords":typekeywords,
                        "tags": tags,
                        "title":title,
                        "description":description, 
                        "culture": self._gis.properties.user.culture,
                        "properties":{
                                    'hasSeenGlobalNav': True, 
                                    'createdFrom': 'defaultInitiativeSiteTemplate', 
                                    'schemaVersion': 1.2, 
                                    'collaborationGroupId': self._initiative.properties['collaborationGroupId'], 
                                    'contentGroupId': self._initiative.properties['contentGroupId'], 
                                    'followersGroupId': self._initiative.properties['followersGroupId'], 
                                    'parentInitiativeId': self._initiative.id, 
                                    'children': []
                                    }, 
                        "url":domain
                        }
            _datafile = 'init-sites-data.json'
            content_group_id = self._initiative.properties['contentGroupId']
            collab_group_id = self._initiative.properties['collaborationGroupId']
            collab_group = self._gis.groups.get(collab_group_id)
            
        
        #Non Hub Sites
        else:
            #Defining content, collaboration groups
            _content_group_dict = {"title": subdomain + ' Content', "tags": ["Hub Group", "Hub Content Group", "Hub Site Group", "Hub Initiative Group"], "access":"public"}
            _collab_group_dict = {"title": subdomain + ' Core Team', "tags": ["Hub Group", "Hub Initiative Group", "Hub Site Group", "Hub Core Team Group", "Hub Team Group"], "access":"org"}
            #Create groups
            content_group =  self._gis.groups.create_from_dict(_content_group_dict)
            content_group_id = content_group.id
            collab_group =  self._gis.groups.create_from_dict(_collab_group_dict)
            #Protect groups from accidental deletion
            content_group.protected = True
            collab_group.protected = True
            _item_dict = {
                        "type": item_type, 
                        "typekeywords":typekeywords, 
                        "tags": tags, 
                        "title":title, 
                        "description":description,
                        "properties":{
                                    'hasSeenGlobalNav': True, 
                                    'createdFrom': 'solutionPortalSiteTemplate', 
                                    'schemaVersion': 1.2, 
                                    'contentGroupId': content_group_id,
                                    'collaborationGroupId': collab_group.id,
                                    'children': []
                                    }, 
                        "url":domain
                        }
            _datafile = 'sites-data.json'

        #Create site item, share with group
        site = self._gis.content.add(_item_dict, owner=self._gis.users.me.username)

        #Share with necessary group
        site.share(groups=[collab_group])

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

    def clone(self, site, title=None):
        """
        Clone allows for the creation of a site that is derived from the current site.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        site                Required Site object of site to be cloned.
        ---------------     --------------------------------------------------------------------
        title               Optional String.
        ===============     ====================================================================
        :return:
           Site.
        """
        from datetime import timezone
        now = datetime.now(timezone.utc)
        #Checking if item of correct type has been passed 
        if 'hubSite' not in site.item.typeKeywords:
            raise Exception("Incorrect item type. Site item needed for cloning.")
        #New title
        if title is None:
            title = site.title + "-copy-%s" % int(now.timestamp() * 1000)
        if self._initiative is None:
            if self._hub._hub_enabled:
                self._hub.initiatives.add(title, site=site)
        subdomain = title.replace(' ', '-').lower()
        if self._gis._portal.is_arcgisonline:
            item_type = "Hub Site Application"
            typekeywords = "Hub, hubSite, hubSolution, JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map, Registered App"
            description = "DO NOT DELETE OR MODIFY THIS ITEM. This item is managed by the ArcGIS Hub application. To make changes to this site, please visit https://hub.arcgis.com/admin/"
            domain = self._gis.url[:8] + subdomain + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com'
    
        else:
            item_type = "Site Application"
            typekeywords = "Hub, hubSite, hubSolution, hubsubdomain|" +subdomain+", JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map"
            domain = 'https://' + self._gis.url[7:] + '/apps/sites/#/'+subdomain
        _site_properties = {
                        "type":item_type, 
                        "typekeywords":typekeywords, 
                        "tags": ["Hub Site"], 
                        "title":title, 
                        "properties":{
                                    'hasSeenGlobalNav': True, 
                                    'schemaVersion': 1, 
                                    },
                        "url":domain
        }
        #Updating properties, groups for initiative sites
        if self._initiative is not None:
            _site_properties["properties"] = {
                                            'hasSeenGlobalNav': True, 
                                            'createdFrom': 'defaultInitiativeSiteTemplate', 
                                            'schemaVersion': 1.2, 
                                            'collaborationGroupId': self._initiative.properties['collaborationGroupId'], 
                                            'contentGroupId': self._initiative.properties['contentGroupId'], 
                                            'followersGroupId': self._initiative.properties['followersGroupId'], 
                                            'parentInitiativeId': self._initiative.id, 
                                            'children': []
                                        }
            content_group_id = self._initiative.properties['contentGroupId']
            collab_group_id = self._initiative.properties['collaborationGroupId']
            collab_group = self._gis.groups.get(collab_group_id)
        else:
            #Defining content, collaboration groups
            _content_group_dict = {"title": subdomain + ' Content', "tags": ["Hub Group", "Hub Content Group", "Hub Site Group", "Hub Initiative Group"], "access":"public"}
            _collab_group_dict = {"title": subdomain + ' Core Team', "tags": ["Hub Group", "Hub Initiative Group", "Hub Site Group", "Hub Core Team Group", "Hub Team Group"], "access":"org"}
            #Create groups
            content_group =  self._gis.groups.create_from_dict(_content_group_dict)
            content_group_id = content_group.id
            collab_group =  self._gis.groups.create_from_dict(_collab_group_dict)
            collab_group_id = collab_group.id
            #Protect groups from accidental deletion
            content_group.protected = True
            collab_group.protected = True
            
        #Create site item, share with group
        new_site = self._gis.content.add(_site_properties, owner=self._gis.users.me.username)

        #Share with necessary group
        new_site.share(groups=[collab_group])

        #Register new site and update its data
        _data = self._create_and_register_site(new_site, subdomain, site.definition, content_group_id, collab_group_id)

        new_site.update(item_properties={'text': _data, 'url': domain})
        return Site(self._gis, new_site)

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
            USAGE EXAMPLE: Fetch an initiative successfully
            site1 = myHub.sites.get('itemId12345')
            site1.item
        """
        siteItem = self._gis.content.get(site_id)
        if 'hubSite' in siteItem.typeKeywords:
            return Site(self._gis, siteItem)
        else:
            raise TypeError("Item is not a valid site or is inaccessible.")
            
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