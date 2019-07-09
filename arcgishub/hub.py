from arcgis.gis import GIS
from arcgis.features import FeatureLayer
from arcgis._impl.common._mixins import PropertyMap
import collections
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

class Hub(object):
    """
    Entry point into the Hub module. Lets you access an individual hub and its components.
       

    ================    ===============================================================
    **Argument**        **Description**
    ----------------    ---------------------------------------------------------------
    url                 Required string. If no URL is provided by user while connecting 
                        to the GIS, then the URL will be ArcGIS Online.
    ----------------    ---------------------------------------------------------------
    username            Optional string as entered while connecting to GIS. The login user name 
                        (case-sensitive).
    ----------------    ---------------------------------------------------------------
    password            Optional string as entered while connecting to GIS. If a username is 
                        provided, a password is expected.  This is case-sensitive. If the password 
                        is not provided, the user is prompted in the interactive dialog.
    ================    ===============================================================

    """
    
    def __init__(self, url, username=None, password=None):
        self.url = url
        self._username = username
        self._password = password
        self.gis = GIS(self.url, self._username, self._password)
        try:
            self._gis_id = self.gis.properties.id
        except AttributeError:
            self._gis_id = None
            
    @property
    def enterprise_org_id(self):
        """
        Returns the AGOL org id of the Enterprise Organization associated with this Hub.
        """
        try:
            self.gis.properties.portalProperties.hub
            try:
                return self.gis.properties.portalProperties.hub.settings.enterpriseOrg.orgId
            except AttributeError: 
                return  self._gis_id
        except:
            print("Hub does not exist or is inaccessible.")
            raise
                        
    @property
    def community_org_id(self):
        """
        Returns the AGOL org id of the Community Organization associated with this Hub.
        """
        try:
            self.gis.properties.portalProperties.hub
            try:
                return self.gis.properties.portalProperties.hub.settings.communityOrg.orgId
            except AttributeError:
                return  self._gis_id
        except:
            print("Hub does not exist or is inaccessible.")
            raise  
  
    @property
    def enterprise_org_url(self):
        """
        Returns the AGOL org url of the Enterprise Organization associated with this Hub.
        """
        try:
            self.gis.properties.portalProperties.hub
            try:
                self.gis.properties.portalProperties.hub.settings.enterpriseOrg
                try:
                    _url = self.gis.properties.publicSubscriptionInfo.companionOrganizations[0]['organizationUrl']
                except:
                    _url = self.gis.properties.subscriptionInfo.companionOrganizations[0]['organizationUrl']
                return "https://"+_url
            except AttributeError: 
                return self.gis.url
        except AttributeError:
            print("Hub does not exist or is inaccessible.")
            raise
        
    @property
    def community_org_url(self):
        """
        Returns the AGOL org id of the Community Organization associated with this Hub.
        """
        try:
            self.gis.properties.portalProperties.hub
            try:
                self.gis.properties.portalProperties.hub.settings.communityOrg
                try:
                    _url = self.gis.properties.publicSubscriptionInfo.companionOrganizations[0]['organizationUrl']
                except:
                    _url = self.gis.properties.subscriptionInfo.companionOrganizations[0]['organizationUrl']
                return "https://"+_url
            except AttributeError: 
                return self.gis.url
        except:
            print("Hub does not exist or is inaccessible.")
            raise
    
    @_lazy_property
    def initiatives(self):
        """
        The resource manager for Hub initiatives. See :class:`~arcgis.apps.hub.InitiativeManager`.
        """
        return InitiativeManager(self)
    
    @_lazy_property
    def events(self):
        """
        The resource manager for Hub events. See :class:`~arcgis.apps.hub.EventManager`.
        """
        return EventManager(self)
    
class Initiative(collections.OrderedDict):
    """
    Represents an initiative within a Hub. An Initiative supports 
    policy- or activity-oriented goals through workflows, tools and team collaboration.
    """
    
    def __init__(self, gis, initiativeItem):
        """
        Constructs an empty Initiative object
        """
        self.item = initiativeItem
        self._gis = gis
        try:
            self._initiativedict = self.item.get_data()
            pmap = PropertyMap(self._initiativedict)
            self.definition = pmap
        except:
            self.definition = None
            
    def __repr__(self):
        return '<%s title:"%s" owner:%s>' % (type(self).__name__, self.title, self.owner)
       
    @property
    def itemid(self):
        """
        Returns the item id of the initiative item
        """
        return self.item.id
    
    @property
    def title(self):
        """
        Returns the title of the initiative item
        """
        return self.item.title
    
    @property
    def description(self):
        """
        Getter/Setter for the initiative description
        """
        return self.item.description
    
    @description.setter
    def description(self, value):
        self.item.description = value
    
    @property
    def snippet(self):
        """
        Getter/Setter for the initiative snippet
        """
        return self.item.snippet
    
    @snippet.setter
    def snippet(self, value):
        self.item.snippet = value
    
    @property
    def owner(self):
        """
        Returns the owner of the initiative item
        """
        return self.item.owner

    @property
    def tags(self):
        """
        Returns the tags of the initiative item
        """
        return self.item.tags
    
    @property
    def url(self):
        """
        Returns the url of the initiative editor
        """
        return self.item.properties['url']
    
    @property
    def site_url(self):
        """
        Returns the url of the initiative site
        """
        return self.item.url
    
    @_lazy_property
    def indicators(self):
        """
        The resource manager for an Initiative's indicators. 
        See :class:`~arcgis.apps.hub.IndicatorManager`.
        """
        return IndicatorManager(self._gis, self.item)
    
    def delete(self):
        """
        Deletes the initiative. If unable to delete, raises a RuntimeException.

        :return:
            A bool containing True (for success) or False (for failure). 

        .. code-block:: python

            USAGE EXAMPLE: Delete an initiative successfully

            initiative1 = myHub.initiatives.get('itemId12345')
            initiative1.delete()

            >> True
        """
        if self.item is not None:
            #Fetch Initiative Collaboration group
            _collab_groupId = self.item.properties['groupId']
            _collab_group = self._gis.groups.get(_collab_groupId)
            #Fetch Open Data Group
            _od_groupId = self.item.properties['openDataGroupId']
            _od_group = self._gis.groups.get(_od_groupId)
            #Disable delete protection on groups
            _collab_group.protected = False
            _od_group.protected = False
            #Delete groups and initiative
            _collab_group.delete()
            _od_group.delete()
            return self.item.delete()
    
    def update(self, initiative_properties=None, data=None, thumbnail=None, metadata=None):
        """ Updates the initiative.


        .. note::
            For initiative_properties, pass in arguments for only the properties you want to be updated.
            All other properties will be untouched.  For example, if you want to update only the
            initiative's description, then only provide the description argument in initiative_properties.


        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        initiative_properties     Required dictionary. See URL below for the keys and values.
        ---------------------     --------------------------------------------------------------------
        data                      Optional string. Either a path or URL to the data.
        ---------------------     --------------------------------------------------------------------
        thumbnail                 Optional string. Either a path or URL to a thumbnail image.
        ---------------------     --------------------------------------------------------------------
        metadata                  Optional string. Either a path or URL to the metadata.
        =====================     ====================================================================


        To find the list of applicable options for argument initiative_properties - 
        https://esri.github.io/arcgis-python-api/apidoc/html/arcgis.gis.toc.html#arcgis.gis.Item.update

        :return:
           A boolean indicating success (True) or failure (False).

        .. code-block:: python

            USAGE EXAMPLE: Update an initiative successfully

            initiative1 = myHub.initiatives.get('itemId12345')
            initiative1.update(initiative_properties={'description':'Create your own initiative to organize people around a shared goal.'})

            >> True
        """
        if initiative_properties:
            _initiative_data = self.definition
            for key, value in initiative_properties.items():
                _initiative_data[key] = value
            return self.item.update(_initiative_data, data, thumbnail, metadata)
    
class InitiativeManager(object):
    """
    Helper class for managing initiatives within a Hub. This class is not created by users directly. 
    An instance of this class, called 'initiatives', is available as a property of the Hub object. Users
    call methods on this 'initiatives' object to manipulate (add, get, search, etc) initiatives.
    """
    
    def __init__(self, hub, initiative=None):
        self._hub = hub
        self._gis = self._hub.gis
          
    def add(self, title, description=None, data=None, thumbnail=None):
        """ 
        Adds a new initiative to the Hub.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        title               Required string.
        ---------------     --------------------------------------------------------------------
        description         Optional string. 
        ---------------     --------------------------------------------------------------------
        data                Optional string. Either a path or URL to the data.
        ---------------     --------------------------------------------------------------------
        thumbnail           Optional string. Either a path or URL to a thumbnail image.
        ===============     ====================================================================

        :return:
           The initiative if successfully added, None if unsuccessful.

        .. code-block:: python

            USAGE EXAMPLE: Add an initiative successfully

            initiative1 = myHub.initiatives.add(title='Vision Zero Analysis')
            initiative1.item
        """

        #Define initiative
        if description is None:
            description = 'Create your own initiative to organize people around a shared goal.'
        _item_dict = {"type":"Hub Initiative", "snippet":title + " Custom initiative", "typekeywords":"OpenData, Hub, hubInitiative", "title":title, "description": description, "licenseInfo": "CC-BY-SA","culture": "{{culture}}", "properties":{'schemaVersion':2}}
        
        #Defining open data and collaboration groups
        _od_group_title = title + ' Initiative Content Group'
        _od_group_dict = {"title": _od_group_title, "tags": ["Hub Initiative Group", "Open Data"], "access":"public", "isOpenData": True}
        _collab_group_title = title + ' Initiative Collaboration Group'
        _collab_group_dict = {"title": _collab_group_title, "tags": ["Hub Initiative Group", "initiativeCollaborationGroup"], "access":"org"}
        
        #Create groups
        od_group =  self._gis.groups.create_from_dict(_od_group_dict)
        collab_group =  self._gis.groups.create_from_dict(_collab_group_dict)
        
        #Protect groups from accidental deletion
        od_group.protected = True
        collab_group.protected = True
        
        #Adding it to _item_dict
        if od_group is not None and collab_group is not None:
            _item_dict['properties']['groupId'] = collab_group.id
            _item_dict['properties']['openDataGroupId'] = od_group.id
        
        #Create initiative and share it with collaboration group
        item =  self._gis.content.add(_item_dict, owner=self._gis.users.me.username)
        item.share(groups=[collab_group])
        
        #update initiative data
        _item_data = {"assets": [{"id": "bannerImage","url": self._hub.enterprise_org_url+"/sharing/rest/content/items/"+item.id+"/resources/detail-image.jpg","properties": {"type": "resource","fileName": "detail-image.jpg","mimeType": "image/jepg"},"license": {"type": "none"},"display": {"position": {"x": "center","y": "center"}}},{"id": "iconDark","url": self._hub.enterprise_org_url+"/sharing/rest/content/items/"+item.id+"/resources/icon-dark.png","properties": {"type": "resource","fileName": "icon-dark.png","mimeType": "image/png"},"license": {"type": "none"}},{"id": "iconLight","url": self._hub.enterprise_org_url+"/sharing/rest/content/items/"+item.id+"/resources/icon-light.png","properties": {"type": "resource","fileName": "icon-light.png","mimeType": "image/png"},"license": {"type": "none"}}],"steps": [{"id": "informTools","title": "Inform the Public","description": "Share data about your initiative with the public so people can easily find, download and use your data in different formats.","templateIds": [],"itemIds": []},{"id": "listenTools","title": "Listen to the Public","description": "Create ways to gather citizen feedback to help inform your city officials.","templateIds": [],"itemIds": []},{"id": "monitorTools","title": "Monitor Progress","description": "Establish performance measures that incorporate the publics perspective.","templateIds": [],"itemIds": []}],"indicators": [],"values": {"collaborationGroupId": collab_group.id,"openDataGroupId": od_group.id,"followerGroups": [],"bannerImage": {"source": "bannerImage","display": {"position": {"x": "center","y": "center"}}}}}
        _data = json.dumps(_item_data)
        item.update(item_properties={'text': _data})
        return Initiative(self._gis, item)
    
    def get(self, initiative_id):
        """ Returns the initiative object for the specified initiative_id.

        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        initiative_id              Required string. The initiative itemid.
        =======================    =============================================================

        :return:
            The initiative object if the item is found, None if the item is not found.

        .. code-block:: python

            USAGE EXAMPLE: Fetch an initiative successfully

            initiative1 = myHub.initiatives.get('itemId12345')
            initiative1.item

        """
        initiativeItem =    self._gis.content.get(initiative_id)
        if 'hubInitiative' in initiativeItem.typeKeywords:
            return Initiative(self._gis, initiativeItem)
        else:
            raise TypeError("Item is not a valid initiative or is inaccessible.")
    
    def search(self, scope=None, title=None, owner=None, created=None, modified=None, tags=None):
        """ 
        Searches for initiatives.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        scope               Optional string. Defines the scope of search.
                            Valid values are 'official', 'community' or 'all'.
        ---------------     --------------------------------------------------------------------
        title               Optional string. Return initiatives with provided string in title.
        ---------------     --------------------------------------------------------------------
        owner               Optional string. Return initiatives owned by a username.
        ---------------     --------------------------------------------------------------------
        created             Optional string. Date the initiative was created.
                            Shown in milliseconds since UNIX epoch.
        ---------------     --------------------------------------------------------------------
        modified            Optional string. Date the initiative was last modified.
                            Shown in milliseconds since UNIX epoch
        ---------------     --------------------------------------------------------------------
        tags                Optional string. User-defined tags that describe the initiative.
        ===============     ====================================================================

        :return:
           A list of matching initiatives.
        """

        initiativelist = []
        
        #Build search query
        query = 'typekeywords:hubInitiative'
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
        
        #Apply org scope and search
        if scope is None or self._gis.url=='https://www.arcgis.com':
            items = self._gis.content.search(query=query, max_items=5000)
        elif scope.lower()=='official':
            query += ' AND access:public'
            _gis = GIS(self._hub.enterprise_org_url)
            items = _gis.content.search(query=query, max_items=5000)
        elif scope.lower()=='community':
            query += ' AND access:public'
            _gis = GIS(self._hub.community_org_url)
            items = _gis.content.search(query=query, max_items=5000)
        elif scope.lower()=='all':
            items = self._gis.content.search(query=query, outside_org=True, max_items=5000)
        else:
            raise Exception("Invalid value for scope")
            
        #Return searched initiatives
        for item in items:
            initiativelist.append(Initiative(self._gis, item))
        return initiativelist
        
class Indicator(collections.OrderedDict):
    """
    Represents an indicator within an initiative. Initiatives use Indicators to standardize 
    data sources for ready-to-use analysis and comparison. Indicators are measurements of a system 
    including features, calculated metrics, or quantified goals. 
    """
    
    def __init__(self, initiativeItem, indicatorObject):
        """
        Constructs an empty Indicator object
        """
        self._initiativeItem = initiativeItem
        self._initiativedata = self._initiativeItem.get_data()
        self._indicatordict = indicatorObject
        pmap = PropertyMap(self._indicatordict)
        self.definition = pmap
            
    def __repr__(self):
        return '<%s id:"%s" optional:%s>' % (type(self).__name__, self.indicatorid, self.optional)
       
    @property
    def indicatorid(self):
        """
        Returns the id of the indicator
        """
        return self._indicatordict['id']
    
    @property
    def indicator_type(self):
        """
        Returns the type (Data/Parameter) of the indicator
        """
        return self._indicatordict['type']
    
    @property
    def optional(self):
        """
        Status if the indicator is optional (True/False)
        """
        return self._indicatordict['optional']
    
    @property
    def url(self):
        """
        Returns the data layer url (if configured) of the indicator
        """
        try:
            return self._indicatordict['source']['url']
        except:
            return 'Url not available for this indicator'
        
    @property
    def name(self):
        """
        Returns the layer name (if configured) of the indicator
        """
        try:
            return self._indicatordict['source']['url']
        except:
            return 'Name not available for this indicator'
        
    @property
    def itemid(self):
        """
        Returns the item id of the data layer (if configured) of the indicator
        """
        try:
            return self._indicatordict['source']['itemId']
        except:
            return 'Item Id not available for this indicator'
        
    @property
    def mappings(self):
        """
        Returns the attribute mapping from data layer (if configured) of the indicator
        """
        try:
            return self._indicatordict['source']['mappings']
        except:
            return 'Attribute mapping not available for this indicator'
    
    def delete(self):
        """
        Deletes an indicator from the initiative

        :return:
            A bool containing True (for success) or False (for failure). 

        .. code-block:: python

            USAGE EXAMPLE: Delete an indicator successfully

            indicator1 = initiative1.indicators.get('streetCrashes')
            indicator1.delete()

            >> True
        """
        if self._indicatordict is not None:
            _indicator_id = self._indicatordict['id']
            self._initiativedata['indicators'] = list(filter(lambda indicator: indicator.get('id')!=_indicator_id, self._initiativedata['indicators']))
            _new_initiativedata = json.dumps(self._initiativedata)
            return self._initiativeItem.update(item_properties={'text': _new_initiativedata})
     
    def get_data(self):
        """
        Retrieves the data associated with an indicator
        """
        return self.definition
    
    def update(self, indicator_properties=None):
        """
        Updates properties of an initiative

        :return:
            A bool containing True (for success) or False (for failure). 

        .. code-block:: python

            USAGE EXAMPLE: Update an indicator successfully

            indicator1_data = indicator1.get_data()
            indicator1_data['optional'] = False
            indicator1.update(indicator_properties = indicator1_data)

            >> True

            Refer the indicator definition (`get_data()`) to learn about fields that can be 
            updated and their acceptable data format.

        """
        try:
            _indicatorId = indicator_properties['id']
        except:
            return 'Indicator properties must include id of indicator'
        if indicator_properties is not None:
            self._initiativedata['indicators'] = [dict(indicator_properties) if indicator['id']==_indicatorId else indicator for indicator in self._initiativedata['indicators']]
            _new_initiativedata = json.dumps(self._initiativedata)
            status = self._initiativeItem.update(item_properties={'text': _new_initiativedata})      
            if status:
                self.definition = PropertyMap(indicator_properties)
                return status
    
class IndicatorManager(object):
    """Helper class for managing indicators within an initiative. This class is not created by users directly. 
    An instance of this class, called 'indicators', is available as a property of the Initiative object. Users
    call methods on this 'indicators' object to manipulate (add, get, search, etc) indicators of a particular
    initiative.
    """
    def __init__(self, gis, initiativeItem):
        self._gis = gis
        self._initiativeItem = initiativeItem
        self._initiativedata = self._initiativeItem.get_data()
        self._indicators = self._initiativedata['indicators']
        
    def add(self, indicator_properties):
        """
        Adds a new indicator to given initiative.

        *Key:Value Dictionary Options for Argument indicator_properties*

        =================  =====================================================================
        **Key**            **Value**
        -----------------  ---------------------------------------------------------------------
        id                 Required string. Indicator identifier within initiative template
        -----------------  ---------------------------------------------------------------------
        name               Optional string. Indicator name
        -----------------  ---------------------------------------------------------------------
        type               Optional string. Valid values are Data, Parameter.
        -----------------  ---------------------------------------------------------------------
        optional           Required boolean
        -----------------  ---------------------------------------------------------------------
        definition         Optional dictionary. Specification of the Indicator - types, fields
        -----------------  ---------------------------------------------------------------------
        source             Optional dictionary. Reference to an API or collection of data along 
                           with mapping between schemas
        =================  =====================================================================

        :return:
           A bool containing True (for success) or False (for failure).

        .. code-block:: python

            USAGE EXAMPLE: Add an indicator successfully

            indicator1_data = {'id': 'streetCrashes', 'type': 'Data', 'optional':False}
            initiative1.indicators.add(indicator_properties = indicator1_data)

            >> True

        """
        _stemplates = []
        _id = indicator_properties['id']
        _added = False
        
        #Fetch initiative template data
        _itemplateid = self._initiativedata['source']
        _itemplate =    self._gis.content.get(_itemplateid)
        _itemplatedata = _itemplate.get_data()
        
        #Fetch solution templates associated with initiative template
        for step in _itemplatedata['steps']:
            for _stemplateid in step['templateIds']:
                _stemplates.append(_stemplateid)
        
        #Fetch data for each solution template
        for _stemplateid in _stemplates:
            _stemplate =    self._gis.content.get(_stemplateid)
            _stemplatedata = _stemplate.get_data()
            
            #Check if indicator exists in solution
            for indicator in _stemplatedata['indicators']:
                
                #add indicator to initiative
                if indicator['id']==_id:
                    if self.get(_id) is not None:
                        return 'Indicator already exists'
                    else:
                        self._initiativedata['indicators'].append(indicator_properties)
                        _new_initiativedata = json.dumps(self._initiativedata)
                        self._initiativeItem.update(item_properties={'text': _new_initiativedata})
                        _added = True
                        return Indicator(self._initiativeItem, indicator_properties)
        if not _added:
            return 'Invalid indicator id for this initiative'
    
    def get(self, indicator_id):
        """ Returns the indicator object for the specified indicator_id.

        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        indicator_id               Required string. The indicator identifier.
        =======================    =============================================================

        :return:
            The indicator object if the indicator is found, None if the indicator is not found.

        """
        for indicator in self._indicators:
            if indicator['id']==indicator_id:
                _indicator = indicator
        try:
            return Indicator(self._initiativeItem, _indicator)
        except:
            return None
    
    def search(self, url=None, item_id=None, name=None):
        """ 
        Searches for indicators within an initiative.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        url                 Optional string. url registered for indicator in `source` dictionary.
        ---------------     --------------------------------------------------------------------
        item_id             Optional string. itemid registered for indicator in `source` dictionary.
        ---------------     --------------------------------------------------------------------
        name                Optional string. name registered for indicator in `source` dictionary.
        ===============     ====================================================================

        :return:
           A list of matching indicators.
        """
        _indicators = []
        indicatorlist = []
        for indicator in self._indicators:
            _indicators.append(indicator)
        if url!=None:
            _indicators = [indicator for indicator in _indicators if indicator['source']['url']==url]
        if item_id!=None:
            _indicators = [indicator for indicator in _indicators if indicator['source']['itemId']==item_id]
        if name!=None:
            _indicators = [indicator for indicator in _indicators if indicator['source']['name']==name]
        for indicator in _indicators:
            indicatorlist.append(Indicator(self._initiativeItem, indicator))
        return indicatorlist

class Event(collections.OrderedDict):
    """
    Represents an event in a Hub. A Hub has many Events that can be associated with an Initiative.
    Events are meetings for people to support an Initiative. Events are scheduled by an organizer 
    and have many attendees. An Event has a Group so that they can include content for preparation 
    as well as gather and archive content during the event for later retrieval or analysis.
    """
    def __init__(self, gis, eventObject):
        """
        Constructs an empty Event object
        """
        self._gis = gis
        self._eventgeometry = eventObject.geometry
        self._eventdict = eventObject.attributes
        pmap = PropertyMap(self._eventdict)
        self.definition = pmap
            
    def __repr__(self):
        return '<%s title:"%s" location:%s>' % (type(self).__name__, self.title, self.location)
    
    @property
    def title(self):
        """
        Returns the title of the event
        """
        return self._eventdict['title']
    
    @property
    def location(self):
        """
        Returns the location of the event
        """
        return self._eventdict['location'] 
    
    @property
    def initiativeid(self):
        """
        Returns the initiative id of the event if it belongs to an Initiative
        """
        return self._eventdict['initiativeId'] 
    
    @property
    def siteid(self):
        """
        Returns the site id of the event site
        """
        return self._eventdict['siteId']
    
    @property
    def organizer_name(self):
        """
        Returns the name of the organizer of the event
        """
        return self._eventdict['organizerName'] 
    
    @property
    def organizers(self):
        """
        Returns names of all organizers of the event
        """
        return self._eventdict['organizers']
    
    @property
    def description(self):
        """
        Returns description of the event
        """
        return self._eventdict['description']
    
    @property
    def start_date(self):
        """
        Returns start date of the event in milliseconds since UNIX epoch
        """
        return self._eventdict['startDate']
    
    @property
    def end_date(self):
        """
        Returns end date of the event in milliseconds since UNIX epoch
        """
        return self._eventdict['endDate']
    
    @property
    def creator(self):
        """
        Returns creator of the event
        """
        return self._eventdict['Creator']
    
    @property
    def capacity(self):
        """
        Returns attendance capacity for attendees of the event
        """
        return self._eventdict['capacity']
    
    @property
    def attendance(self):
        """
        Returns attendance count for a past event
        """
        return self._eventdict['attendance']
    
    @property
    def status(self):
        """
        Returns status of the event
        """
        return self._eventdict['status']
    
    @property
    def is_cancelled(self):
        """
        Check if event is Cancelled
        """
        return self._eventdict['isCancelled']
    
    @property
    def geometry(self):
        """
        Returns co-ordinates of the event location
        """
        return self._eventgeometry
    
class EventManager(object):
    """Helper class for managing events within a Hub. This class is not created by users directly. 
    An instance of this class, called 'events', is available as a property of the Hub object. Users
    call methods on this 'events' object to manipulate (add, search, get_map etc) events 
    of a particular Hub. 
    """
    def __init__(self, hub, event=None):
        self._gis = hub.gis
        if event:
            self._event = event
            
    def __all_events(self):
        """
        Fetches all events for particular hub.
        """
        events = []
        _events_layer = self._gis.content.search(query="typekeywords:hubEventsLayer", max_items=5000)[0]
        _events_layer_url = _events_layer.url + '/0'
        _events_data = FeatureLayer(_events_layer_url).query().features
        for event in _events_data:
            events.append(Event(self._gis, event))
        return events
    
    def search(self, initiative_id=None, title=None, location=None, organizer_name=None):
        """ 
        Searches for events within a Hub.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        initiative_id       Optional string. Initiative itemid.
        ---------------     --------------------------------------------------------------------
        title               Optional string. Title of the event.
        ---------------     --------------------------------------------------------------------
        location            Optional string. Location where event is held.
        ---------------     --------------------------------------------------------------------
        organizer_name      Optional string. Name of the organizer of the event.
        ===============     ====================================================================

        :return:
           A list of matching indicators.
        """
        events = []
        events = self.__all_events()
        if initiative_id!=None:
            events = [event for event in events if initiative_id==event.initiativeid]
        if title!=None:
            events = [event for event in events if title in event.title]
        if location!=None:
            events = [event for event in events if location in event.location]
        if organizer_name!=None:
            events = [event for event in events if organizer_name==event.organizer_name]
        return events
    
    def get_map(self):
        """
        Plot all events for a Hub in an embedded webmap within the notebook.
        """
        _events_layer = self._gis.content.search(query="typekeywords:hubEventsLayer", max_items=5000)[0]
        event_map = self._gis.map(zoomlevel=2)
        event_map.basemap = 'dark-gray'
        event_map.add_layer(_events_layer, {'title':'Event locations for this Hub','opacity':0.7})
        return event_map
