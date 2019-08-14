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
        if not self._gis._portal.is_arcgisonline:
            return self.item.delete()
        if self.item is not None:
            #Fetch site data
            _site_data = self.definition
            #Disable delete protection on site
            self.item.protected = False
            #Delete domain entry
            _HEADERS = {'Content-Type': 'application/json', 'Authorization': self._gis._con.token}
            path = 'https://hub.arcgis.com/utilities/domains/'+_site_data['values']['siteId']
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
    
    def __init__(self, gis, initiative=None):
        self._gis = gis
        self._initiative = initiative

    def _create_and_register_site(self, site, subdomain, site_data, group_ids):
        """
        Registers site as an app and Creates a domain entry for new site. 
        Updates data with necessary attributes for a new site.
        """

        basemap = {}
        _siteId = 'arcgisonline'
        client_key = None

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
            #Check for length of domain
            if len(subdomain) > 63:
                raise ValueError('Requested url too long. Please enter a name shorter than 63 characters')


        #for group_id in group_ids:
        try:
            site_data['catalog']['groups'].append(group_ids)
        except:
            site_data['values']['groups'].append(group_ids)
        if self._gis._portal.is_arcgisonline:
            site_data['catalog'] = {}
            site_data['catalog']['groups'] = [group_ids]
            site_data['values'].pop('groups', None)
            site_data['values']['uiVersion'] = "2.3"
            site_data['values']['theme']['globalNav'] = {}
            site_data['values']['theme']['globalNav'] = self._gis.properties['portalProperties']['sharedTheme']['header']
        else:
            site_data['values']['uiVersion'] = "2.2"

        site_data['values']['title'] = site.title
        site_data['values']['layout']['header']['component']['settings']['title'] = site.title
        #site_data['values']['collaborationGroupId'] = _group.id
        site_data['values']['subdomain'] = subdomain
        site_data['values']['defaultHostname'] = site.url[8:]
        site_data['values']['updatedBy'] = self._gis.users.me.username
        site_data['values']['clientId'] = _siteId
        site_data['values']['siteId'] = client_key
        site_data['values']['extent'] = self._gis.properties['defaultExtent']

        try:
            basemap['url'] = self._gis.properties['defaultBasemap']['baseMapLayers'][0]['styleUrl']
        except KeyError:
            basemap['url'] = self._gis.properties['defaultBasemap']['baseMapLayers'][0]['url']
        basemap['layerType'] = self._gis.properties['defaultBasemap']['baseMapLayers'][0]['layerType']
        site_data['values']['map']['basemaps']['primary']['baseMapLayers'].append(basemap)

        site_data['values']['theme'] = self._gis.properties['portalProperties']['sharedTheme']
        try:
            site_data['values']['theme']['globalNav'] = self._gis.properties['portalProperties']['sharedTheme']['header']
        except KeyError:
            pass
        return site_data

    def add(self, title, subdomain, groups=None):
        """ 
        Adds a new site.
        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        title               Required string.
        ---------------     --------------------------------------------------------------------
        subdomain           Required string.
        ---------------     --------------------------------------------------------------------
        groups              Optional groups object. Represents open data group or initiative
                            collaboration groups for initiative sites.
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
        group_ids = []
        subdomain = subdomain.replace(' ', '-').lower()
        if self._gis._portal.is_arcgisonline:
            item_type = "Hub Site Application"
            typekeywords = "Hub, hubSite, hubSolution, JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map, Registered App"
        else:
            item_type = "Site Application"
            typekeywords = "Hub, hubSite, hubSolution, hubsubdomain|" +subdomain+", JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map"

        #Determining site type
        #Open Data site
        if groups is not None:
            _item_dict = {
                        "type": item_type, 
                        "typekeywords":typekeywords, 
                        "tags": ["Hub Site"], 
                        "title":title, 
                        "properties":{
                                    'hasSeenGlobalNav': True, 
                                    'createdFrom': 'defaultSiteTemplate', 
                                    'schemaVersion': 1, 
                                    'collaborationGroupId': self._gis.properties.portalProperties.openData.settings.groupId
                                    }, 
                        "url":subdomain
                        }
            _group = self._gis.groups.get(self._gis.properties.portalProperties.openData.settings.groupId)
            _datafile = 'od-sites-data.json'
            for group in groups:
                group_ids.append(group.id)
        #Initiative Site
        else:
            _item_dict = {
                        "type":item_type, 
                        "typekeywords":typekeywords,
                        "tags": ["Hub Site"], 
                        "title":title, 
                        "properties":{
                                    'hasSeenGlobalNav': True, 
                                    'createdFrom': 'defaultInitiativeSiteTemplate', 
                                    'schemaVersion': 1.2, 
                                    'collaborationGroupId': self._initiative.properties['groupId'], 
                                    'parentInitiativeId': self._initiative.id, 
                                    'children': []
                                    }, 
                        "url":subdomain
                        }
            _group = self._gis.groups.get(self._initiative.properties['groupId'])
            _datafile = 'init-sites-data.json'
            group_ids = group_ids.append(self._initiative.properties['openDataGroupId'])

        #For Hub Sites
        if self._gis._portal.is_arcgisonline:

            #Domain manipulation
            domain = self._gis.url[:8] + subdomain + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com'
            _request_url = 'https://hub.arcgis.com/utilities/domains/'+domain[8:]
            _response = requests.get(_request_url)
        
            #Check if domain doesn't exist
            if _response.status_code==404:
                pass
            else:
            #If exists check if counter needs updating and update it for initiative sites
                if _datafile == 'init-sites-data.json':
                    try:
                        count = int(subdomain[-1])
                        count = count + 1
                        subdomain = subdomain[:-1] + str(count)
                    except:
                        subdomain = subdomain + '1'
                    domain = self._gis.url[:8] + subdomain + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com'
                else:
                    #Request another subdomain for opendata sites
                    raise ValueError("You already have a site that uses this subdomain. Please provide another subdomain.")
        #For Enterprise Sites
        else:
            #Domain manipulation
            domain = self._gis.url + '/apps/sites/#/'+subdomain

            #Check if site subdomain exists
            if self._gis.content.search(query='typekeywords:hubsubdomain|'+subdomain+' AND title:'+title):
                print(self._gis.content.search(query='typekeywords:hubsubdomain|'+subdomain))
                raise ValueError("You already have a site that uses this subdomain. Please provide another subdomain.")

        #Create site item, share with group
        site = self._gis.content.add(_item_dict, owner=self._gis.users.me.username)

        #Share with necessary group
        site.share(groups=[_group])

        #protect site from accidental deletion if it is an initiative site
        if _datafile == 'init-sites-data.json':
            site.protected = True

        #Setting data for site
        data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '_store/'+_datafile))
        
        with open(data_path) as f:
            _site_data = json.load(f)
       
        #Register site and update its data
        _data = self._create_and_register_site(site, subdomain, _site_data, group_ids)

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
        if title is None:
            title = site.title + "-copy-%s" % int(now.timestamp() * 1000)
        subdomain = title.replace(' ', '-').lower()
        if self._gis._portal.is_arcgisonline:
            item_type = "Hub Site Application"
            typekeywords = "Hub, hubSite, hubSolution, JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map, Registered App"
            domain = self._gis.url[:8] + subdomain + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com'
    
        else:
            item_type = "Site Application"
            typekeywords = "Hub, hubSite, hubSolution, hubsubdomain|" +subdomain+", JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map"
            domain = self._gis.url + '/apps/sites/#/'+subdomain
        _site_properties = {
                        "type":item_type, 
                        "typekeywords":typekeywords, 
                        "tags": ["Hub Site"], 
                        "title":title, 
                        "properties":{
                                    'hasSeenGlobalNav': True, 
                                    #'createdFrom': site.item.properties['createdFrom'], 
                                    'schemaVersion': 1, 
                                    },
                        "url":domain
        }

        #Create group for site
        _od_group_title = title + ' Site Content Group'
        _od_group_dict = {"title": _od_group_title, "access":"public", "isOpenData": True}
        od_group =  self._gis.groups.create_from_dict(_od_group_dict)
        od_group.protected = True

        #Create site item, share with group
        new_site = self._gis.content.add(_site_properties, owner=self._gis.users.me.username)

        #Share with necessary group
        new_site.share(groups=[od_group])

        #Register new site and update its data
        _data = self._create_and_register_site(new_site, subdomain, site.definition, od_group.id)

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