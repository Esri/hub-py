from arcgis.gis import GIS
from arcgis.features import FeatureLayer
from arcgis._impl.common._mixins import PropertyMap
import collections
import requests
import json

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
        Constructs an empty Initiative object
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
    
    @property
    def url(self):
        """
        Returns the url of the site
        """
        return self.item.url
    
class SiteManager(object):
    """
    Helper class for managing sites within a Hub. This class is not created by users directly. 
    An instance of this class, called 'sites', is available as a property of the Hub object. Users
    call methods on this 'sites' object to manipulate (add, get, search, etc) sites.
    """
    
    def __init__(self, gis, initiative=None):
        self._gis = gis
        self._initiative = initiative

    def add(self, title, domain, group_id=None):
        """ 
        Adds a new site.
        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        title               Required string.
        ---------------     --------------------------------------------------------------------
        domain              Required string.
        ---------------     --------------------------------------------------------------------
        group_id            Optional string. Represents open data group_id or initiative
                            collaboration group_id for initiative sites.
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
        domain_str = domain.replace(' ', '-').lower()

        #Determining site type
        #Open Data site
        if group_id is not None:
            _item_dict = {"type":"Hub Site Application", "typekeywords":"Hub, hubSite, hubSolution, JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map, Registered App", "tags": ["Hub Site"], "title":title, "properties":{'hasSeenGlobalNav': True, 'createdFrom': 'defaultSiteTemplate', 'schemaVersion': 1, 'collaborationGroupId': self._gis.properties.portalProperties.openData.settings.groupId}, "url":domain}
            _group = self._gis.groups.get(self._gis.properties.portalProperties.openData.settings.groupId)
            _datafile = 'od-sites-data.json'
        #Initiative Site
        else:
            _item_dict = {"type":"Hub Site Application", "typekeywords":"Hub, hubSite, hubSolution, JavaScript, Map, Mapping Site, Online Map, OpenData, Ready To Use, selfConfigured, Web Map, Registered App", "tags": ["Hub Site"], "title":title, "properties":{'hasSeenGlobalNav': True, 'createdFrom': 'defaultInitiativeSiteTemplate', 'schemaVersion': 1.2, 'collaborationGroupId': self._initiative.properties['groupId'], 'parentInitiativeId': self._initiative.id, 'children': []}, "url":domain}
            _group = self._gis.groups.get(self._initiative.properties['groupId'])
            _datafile = 'init-sites-data.json'
            group_id = self._initiative.properties['openDataGroupId']

        #Domain manipulation
        domain = self._gis.url[:8] + domain_str + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com'
        _request_url = 'https://hub.arcgis.com/utilities/domains?orgId='+domain[8:]
        _response = requests.get(_request_url)
        
        #Check if domain doesn't exist
        try:
            if _response.status_code==404:
                pass
        except:
        #If exists check if counter needs updating and update it
            try:
                count = int(domain_str[-1])
                count = count + 1
                domain_str = domain_str[:-1] + str(count)
            except:
                domain_str = domain_str + '1'
        domain = self._gis.url[:8] + domain_str + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com'

        #Create site item, share with group
        site = self._gis.content.add(_item_dict, owner=self._gis.users.me.username)

        #Share with necessary group
        site.share(groups=[_group])

        #protect site from accidental deletion if it is an initiative site
        if _datafile == 'init-sites-data.json':
            site.protected = True

        #register site as an app
        _app_dict = site.register(app_type='browser', redirect_uris=[domain])
        _client_key = _app_dict['client_id']

        #Create domain entry for new site
        _HEADERS = {'Content-Type': 'application/json', 'Authorization': self._gis._con.token}
        _body = {'hostname': domain_str + '-' + self._gis.properties['urlKey'] + '.hub.arcgis.com', 'siteId': site.id, 'siteTitle': title, 'clientKey': _client_key, 'orgId': self._gis.properties.id, 'orgKey': self._gis.properties['urlKey'], 'orgTitle':self._gis.properties['name']}
        _new_domain = requests.post('https://hub.arcgis.com/utilities/domains', headers = _HEADERS, data=json.dumps(_body))
        if _new_domain.status_code==200:
            _siteId = _new_domain.json()['id']
    
        #Setting data for site
        with open(_datafile) as f:
            _site_data = json.load(f)
        _basemap = {}
        _theme = {}
        _site_data['catalog']['groups'].append(group_id)
        _site_data['values']['title'] = title
        _site_data['values']['layout']['header']['component']['settings']['title'] = title
        _site_data['values']['collaborationGroupId'] = _group.id
        _site_data['values']['subdomain'] = domain_str
        _site_data['values']['defaultHostname'] = domain
        _site_data['values']['updatedBy'] = self._gis.users.me.username
        _site_data['values']['clientId'] = _client_key
        _site_data['values']['siteId'] = _siteId
        _site_data['values']['extent'] = self._gis.properties['defaultExtent']

        _basemap['url'] = self._gis.properties['defaultBasemap']['baseMapLayers'][0]['url']
        _basemap['layerType'] = self._gis.properties['defaultBasemap']['baseMapLayers'][0]['layerType']
        _site_data['values']['map']['basemaps']['primary']['baseMapLayers'].append(_basemap)

        _site_data['values']['theme'] = self._gis.properties['portalProperties']['sharedTheme']
        _site_data['values']['theme']['globalNav'] = self._gis.properties['portalProperties']['sharedTheme']['header']

        _data = json.dumps(_site_data)
        site.update(item_properties={'text': _data, 'url': domain})
        return Site(self._gis, site)
        
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
        
        #Ssearch
        items = self._gis.content.search(query=query, max_items=5000)
        
        #Return searched sites
        for site in sites:
            sitelist.append(Site(self._gis, site))
        return sitelist