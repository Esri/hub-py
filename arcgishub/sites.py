from arcgis.gis import GIS
from arcgis._impl.common._mixins import PropertyMap
from arcgis._impl.common._isd import InsensitiveDict
from arcgishub.pages import Page, PageManager
from datetime import datetime
from collections import OrderedDict
from urllib.parse import urlparse
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
    def initiative_id(self):
        """
        Returns the initiative id (if available) of the site
        """
        try:
            return self.item.properties['parentInitiativeId']
        except:
            return None

    @_lazy_property
    def initiative(self):
        """
        Returns the initiative object (if available) for the site
        """
        try:
            return self._gis.hub.initiatives.get(self.initiative_id)
        except:
            return None

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
            return self.item.properties["collaborationGroupId"]
        except:
            if self._gis.hub._hub_enabled:
                return self.initiative.collab_group_id
            else:
                return None

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
        **Parameter**              **Description**
        ---------------------     --------------------------------------------------------------------
        items_list                Required list. A list of Item or item ids to add to the site.
        =====================     ====================================================================
        """
        # If input list is of item_ids, generate a list of corresponding items
        if type(items_list[0]) == str:
            items = [self._gis.content.get(item_id) for item_id in items_list]
        else:
            items = items_list
        # Fetch existing sharing privileges for each item, to retain them after adding to content library
        for item in items:
            sharing = item.shared_with
            everyone = sharing["everyone"]
            org = sharing["org"]
            groups = sharing["groups"]
            # add current site's content group to list of groups to share to
            groups.append(self.content_group_id)
            # share item to this group
            status = item.share(everyone=everyone, org=org, groups=groups)
            if status["results"][0]["success"] == False:
                return status
        return status

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
        # Fetch Site Collaboration group if exists
        _collab_group = None
        try:
            _collab_group_id = self.collab_group_id
            _collab_group = self._gis.groups.get(_collab_group_id)
            _collab_group.protected = False
            _collab_group.delete()
        except:
            pass
        # Fetch Content Group
        _content_group_id = self.content_group_id
        _content_group = self._gis.groups.get(_content_group_id)
        # Disable delete protection on groups and site
        try:
            _content_group.protected = False
            self.item.protect(enable=False)
            # Delete groups, site
            _content_group.delete()
        except:
            pass
        #Delete enterprise site
        if not self._gis._portal.is_arcgisonline:
            return self.item.delete()
        else:
            #Deleting hub sites
            if self.item is not None:
                #Fetch site data
                _site_data = self.definition
                #Disable delete protection on site
                self.item.protect(enable=False)
                # Fetch siteId from domain entry
                path = "https://hub.arcgis.com/api/v3/domains?siteId=" + self.itemid
                _site_domain = self._gis._con.get(path=path)
                _siteId = _site_domain[0]["id"]
                # Delete domain entry
                session = self._gis._con._session
                headers = {k: v for k, v in session.headers.items()}
                headers["Content-Type"] = "application/json"
                headers["Authorization"] = "X-Esri-Authorization"
                path = "https://hub.arcgis.com/api/v3/domains/" + _siteId
                _delete_domain = session.delete(url=path, headers=headers)
                if _delete_domain.status_code == 200:
                    # Delete site item
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
                    "membershipAccess": "org",
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

    def update(self, site_properties=None, subdomain=None):
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
        subdomain                 Optional string. New subdomain for the site.
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
        _site_data = self.definition
        if site_properties:
            for key, value in site_properties.items():
                _site_data[key] = value
        if subdomain:
            # format subdomain if needed
            subdomain = subdomain.replace(" ", "-").lower()
            #Domain manipulation for new subdomain
            if self._gis._portal.is_arcgisonline:
                #Check for length of domain
                if len(subdomain + '-' + self._gis.properties['urlKey']) > 63:
                    _num = 63 - len(self._gis.properties['urlKey'])
                    raise ValueError('Requested url too long. Please enter a subdomain shorter than %d characters' %_num)
                # Fetch siteId from domain entry
                path = "https://hub.arcgis.com/api/v3/domains?siteId=" + self.itemid
                _site_domain = self._gis._con.get(path=path)
                _siteId = _site_domain[0]["id"]
                client_key = _site_domain[0]["clientKey"]
                # Delete old domain entry
                session = self._gis._con._session
                headers = {k: v for k, v in session.headers.items()}
                headers["Content-Type"] = "application/json"
                headers["Authorization"] = "X-Esri-Authorization"
                path = "https://hub.arcgis.com/api/v3/domains/" + _siteId
                _delete_domain = session.delete(url=path, headers=headers)
                # if deletion is successful
                if _delete_domain.status_code == 200:
                    # Create new domain entry

                    # Create domain entry for new site
                    _HEADERS = {
                        "Content-Type": "application/json",
                        "Authorization": "X-Esri-Authorization",
                        "Referer": self._gis._con._referer,
                    }
                    _body = {
                        "hostname": subdomain
                        + "-"
                        + self._gis.properties["urlKey"]
                        + ".hub.arcgis.com",
                        "siteId": self.item.id,
                        "siteTitle": self.title,
                        "orgId": self._gis.properties.id,
                        "orgKey": self._gis.properties["urlKey"],
                        "orgTitle": self._gis.properties["name"],
                        "sslOnly": True,
                    }
                    headers = {k: v for k, v in session.headers.items()}
                    headers["Content-Type"] = "application/json"
                    headers["Authorization"] = "X-Esri-Authorization"
                    _new_domain = session.post(
                        url="https://hub.arcgis.com/api/v3/domains",
                        data=json.dumps(_body),
                        headers=headers,
                    )
                    if _new_domain.status_code == 200:
                        # define new domain and hostname
                        hostname = (
                            subdomain
                            + "-"
                            + self._gis.properties["urlKey"]
                            + ".hub.arcgis.com"
                        )
                        domain = self._gis.url[:8] + hostname
                        _client_key = _new_domain.json()["clientKey"]
                        # update initiative item
                        if self._gis.hub._hub_enabled:
                            self.initiative.item.update(item_properties={"url": domain})
                        # update site item and data
                        data = self.definition
                        data["values"]["defaultHostname"] = hostname
                        data["values"]["subdomain"] = subdomain
                        data["values"]["internalUrl"] = hostname
                        if self.item.update(
                            item_properties={"url": domain, "text": data}
                        ):
                            return domain
                    # if creating new domain entry fails
                    else:
                        return _new_domain.content
                # if deleting old domain entry fails
                else:
                    return _delete_domain.content
            #For enterprise sites
            else:
                #Check for length of domain
                if len(subdomain) > 63:
                    raise ValueError('Requested url too long. Please enter a name shorter than 63 characters')
                typeKeywords = self.item.typeKeywords
                typeKeywords = [keyword for keyword in typeKeywords if 'hubsubdomain' not in keyword]
                typeKeywords.append('hubsubdomain|'+subdomain)
                #Domain manipulation
                hostname = self._gis.url[7:-5] + '/apps/sites/#/'+subdomain
                domain = 'https://' + hostname
                data = self.definition
                data['values']['defaultHostname'] = hostname
                data['values']['subdomain'] = subdomain
                data['values']['internalUrl'] = hostname
                data["values"]["clientId"] = _client_key
                if self.item.update(item_properties={'typeKeywords':typeKeywords, 'url':domain, 'text':data}):
                    return domain
        return self.item.update(_site_data)

    
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
        # Deleting the draft file for this site, if exists
        resources = self.item.resources.list()
        for resource in resources:
            if "draft-" in resource["resource"]:
                self.item.resources.remove(file=resource["resource"])
        # Update the data of the site
        self.definition["values"]["layout"] = layout._json()
        return self.item.update(item_properties={"text": self.definition})

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
            if "draft-" in resource["resource"]:
                self.item.resources.remove(file=resource["resource"])
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

            #Check for length of domain
            if len(subdomain + '-' + self._gis.properties['urlKey']) > 63:
                _num = 63 - len(self._gis.properties['urlKey'])
                raise ValueError('Requested url too long. Please enter a name shorter than %d characters' %_num)

            session = self._gis._con._session
            # Create domain entry for new site
            _HEADERS = {
                "Content-Type": "application/json",
                "Authorization": "X-Esri-Authorization",
                "Referer": self._gis._con._referer,
            }
            _body = {
                "hostname": subdomain
                + "-"
                + self._gis.properties["urlKey"]
                + ".hub.arcgis.com",
                "siteId": site.id,
                "siteTitle": site.title,
                "orgId": self._gis.properties.id,
                "orgKey": self._gis.properties["urlKey"],
                "orgTitle": self._gis.properties["name"],
                "sslOnly": True,
            }

            headers = {k: v for k, v in session.headers.items()}
            headers["Content-Type"] = "application/json"
            headers["Authorization"] = "X-Esri-Authorization"
            _new_domain = session.post(
                url="https://hub.arcgis.com/api/v3/domains",
                data=json.dumps(_body),
                headers=headers,
            )
            if _new_domain.status_code == 200:
                _siteId = _new_domain.json()["id"]
                _client_key = _new_domain.json()["clientKey"]
            else:
                return _new_domain
        else:
            # Check for length of domain
            if len(subdomain) > 63:
                raise ValueError(
                    "Requested url too long. Please enter a name shorter than 63 characters"
                )

        # for group_id in group_ids:
        try:
            site_data["catalog"]["groups"].append(content_group_id)
        except:
            site_data["values"]["groups"].append(content_group_id)
            site_data["values"]["uiVersion"] = "2.3"
        if self._gis._portal.is_arcgisonline:
            site_data["values"]["theme"]["globalNav"] = {}
            try:
                site_data["values"]["theme"]["globalNav"] = self._gis.properties[
                    "portalProperties"
                ]["sharedTheme"]["header"]
            except KeyError:
                site_data["values"]["theme"]["globalNav"] = {
                    "background": "#fff",
                    "text": "#000000",
                }
        site_data["values"]["title"] = site.title
        site_data["values"]["layout"]["header"]["component"]["settings"][
            "title"
        ] = site.title
        site_data["values"]["collaborationGroupId"] = collab_group_id
        site_data["values"]["subdomain"] = subdomain
        site_data["values"]["defaultHostname"] = site.url
        site_data["values"]["updatedBy"] = self._gis.users.me.username
        if self._gis._portal.is_arcgisonline:
            site_data["values"]["siteId"] = _siteId
            site_data["values"]["clientId"] = _client_key
        else:
            site_data["values"]["clientId"] = "arcgisonline"
        # Add collaboration group to gallery card only if it exists in the usual spot
        try:
            site_data["values"]["layout"]["sections"][6]["rows"][1]["cards"][0][
                "component"
            ]["settings"]["selectedGroups"][0]["id"] = collab_group_id
        except:
            pass
        # Link follow button to current initiative only if it exists in the usual spot
        if self._gis._portal.is_arcgisonline and self._hub._hub_enabled:
            try:
                site_data["values"]["layout"]["sections"][8]["rows"][1]["cards"][0][
                    "component"
                ]["settings"]["initiativeId"] = self.initiative.itemid
            except:
                pass
        site_data["values"]["map"] = self._gis.properties["defaultBasemap"]
        site_data["values"]["defaultExtent"] = self._gis.properties["defaultExtent"]

        # site_data['values']['theme'] = self._gis.properties['portalProperties']['sharedTheme']
        return site_data

    def add(self, title, subdomain=None):
        """ 
        Adds a new site.

        .. note:: 
            Unicode characters are not allowed in the title of the site.
        
        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        title               Required string.
        ---------------     --------------------------------------------------------------------
        subdomain           Optional string. Available ONLY with Enterprise Sites.
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
        #Checking if subdomain is provided
        if subdomain:
            #disallow for AGO
            if self._gis._portal.is_arcgisonline:
                raise Exception('The option to add sites with custom subdomain is only available with Enterprise Sites. Please add this site without custom subdomain.')
            #re-format if given for Enterprise sites
            else:
                subdomain = subdomain.replace(' ', '-').lower()
        #re-format title if subdomain not provided
        else:
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
            session = self._gis._con._session
            headers = {k: v for k, v in session.headers.items()}
            headers["Content-Type"] = "application/json"
            headers["Authorization"] = "X-Esri-Authorization"
            response = session.get(
                url=f"https://hub.arcgis.com/api/v3/domains/" + domain[8:],
                headers=headers,
            )
        
            #Check if domain doesn't exist
            if response.status_code==404:
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
            domain = 'https://' + self._gis.url[8:-5] + 'apps/sites/#/'+subdomain

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
                _content_group_title = title + ' Content'
                _content_group_dict = {
                    "title": _content_group_title, 
                    "tags": ["Hub Group", "Hub Content Group", "Hub Site Group"], 
                    "access":"public"
                }
                _collab_group_title = title + ' Core Team'
                _collab_group_dict = {
                    "title": _collab_group_title, 
                    "tags": ["Hub Group", "Hub Site Group", "Hub Core Team Group", "Hub Team Group"], 
                    "access":"org",
                    "capabilities":"updateitemcontrol",
                    "membershipAccess": "collaboration",
                    "snippet": "Members of this group can create, edit, and manage the site, pages, and other content related to "+title+"."
                }
                created_from = 'basicDefaultSite Solution Template (embedded)'
            else:
                #Defining content, collaboration groups for Enterprise Sites
                collab_group_id = None
                _content_group_dict = {
                    "title": subdomain + ' Content', 
                    "tags": ["Sites Group", "Sites Content Group"], 
                    "access":"org",
                    "snippet": "Applications, maps, data, etc. shared with this group generates the "+subdomain+" content catalog."
                }
                _collab_group_dict = {
                    "title": subdomain + ' Core Team', 
                    "tags": ["Sites Group", "Sites Core Team Group"], 
                    "access":"org",
                    "capabilities": "updateitemcontrol",
                    "membershipAccess": "org",
                    "snippet": "Members of this group can create, edit, and manage the site, pages, and other content related to "+subdomain+"."
                }
                created_from = 'portalDefaultSite'
            #Create groups
            content_group =  self._gis.groups.create_from_dict(_content_group_dict)
            content_group_id = content_group.id
            #Create collaboration group if necessary privileges exist
            if self._gis.users.me.role=='org_admin':
                collab_group =  self._gis.groups.create_from_dict(_collab_group_dict)
                collab_group.protected = True
                collab_group_id = collab_group.id
            else:
                collab_group_id = None
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
                    'createdFrom': created_from, 
                    'schemaVersion': 1.5, 
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

        .. note:: 
            Use this method if you are cloning a Site object from a Hub Basic or Enterprise environment.
            To clone from Hub Premium environments, please use the `initiatives.clone` method.

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
        #For Hub Sites
        if self._gis._portal.is_arcgisonline:
            item_type = "Hub Site Application"
            typekeywords = "Hub, hubSite, hubSolution, JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map, Registered App"
            description = "DO NOT DELETE OR MODIFY THIS ITEM. This item is managed by the ArcGIS Hub application. To make changes to this site, please visit https://hub.arcgis.com/admin/"
            domain = self._gis.url[:8] + subdomain + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com'
        #For Enterprise Sites
        else:
            item_type = "Site Application"
            typekeywords = "Hub, hubSite, hubSolution, hubsubdomain|" +subdomain+", JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map"
            domain = 'https://' + self._gis.url[8:-5] + 'apps/sites/#/'+subdomain
        _site_properties = {
                        "type":item_type, 
                        "typekeywords":typekeywords, 
                        "tags": ["Enterprise Site"], 
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
            #Defining content, collaboration groups for Hub Basic and Enterprise Sites
            #For Hub Basic Sites
            if self._gis._portal.is_arcgisonline:
                _content_group_dict = {
                    "title": subdomain + ' Content', 
                    "tags": ["Hub Group", "Hub Content Group", "Hub Site Group"], 
                    "access":"public"
                }
                _collab_group_dict = {
                    "title": subdomain + ' Core Team', 
                    "tags": ["Hub Group", "Hub Site Group", "Hub Core Team Group", "Hub Team Group"], 
                    "access":"org",
                    "capabilities":"updateitemcontrol",
                    "membershipAccess": "collaboration",
                    "snippet": "Members of this group can create, edit, and manage the site, pages, and other content related to "+subdomain+"."
                }
                created_from = 'basicDefaultSite Solution Template (embedded)'
            #For Enterprise Sites
            else:
                _content_group_dict = {
                    "title": subdomain + ' Content', 
                    "tags": ["Sites Group", "Sites Content Group"], 
                    "access":"org",
                    "snippet": "Applications, maps, data, etc. shared with this group generates the "+subdomain+" content catalog."
                }
                _collab_group_dict = {
                    "title": subdomain + ' Core Team', 
                    "tags": ["Sites Group", "Sites Core Team Group"], 
                    "access":"org",
                    "capabilities": "updateitemcontrol",
                    "membershipAccess": "org",
                    "snippet": "Members of this group can create, edit, and manage the site, pages, and other content related to "+subdomain+"."
                }
                created_from = 'portalDefaultSite'
            #Create content group
            content_group =  self._gis.groups.create_from_dict(_content_group_dict)
            content_group_id = content_group.id
            #Protect groups from accidental deletion
            content_group.protected = True
            _site_properties["properties"] = {
                                            'hasSeenGlobalNav': True, 
                                            'createdFrom': created_from, 
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
            if "http" in domain_url:
                domain_url = urlparse(domain_url).netloc
            path = "https://hub.arcgis.com/api/v3/domains/" + domain_url
            # fetch site itemid from domain service
            session = self._gis._con._session
            headers = {k: v for k, v in session.headers.items()}
            headers["Content-Type"] = "application/json"
            headers["Authorization"] = "X-Esri-Authorization"
            _site_domain = self._gis._con.get(path, headers=headers)
            try:
                siteId = _site_domain["siteId"]
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
