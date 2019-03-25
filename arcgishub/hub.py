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
    """Entry point. Acceessing an individual hub and its components"""
    
    def __init__(self, url, username=None, password=None):
        self.url = url
        self._username = username
        self._password = password
        self.org = GIS(self.url, self._username, self._password)
        try:
            self._org_id = self.org.properties.id
        except AttributeError:
            return "Invalid Hub"
            sys.exit(0)
            
    @property
    def enterprise_orgId(self):
        '''Get the enterprise org id for this hub'''
        try:
            return self.org.properties.portalProperties.hub.settings.enterpriseOrg.orgId
        except AttributeError: 
            return self._org_id
            
    @property
    def community_orgId(self):
        '''Get the community org id for this hub'''
        try:
            return self.org.properties.portalProperties.hub.settings.communityOrg.orgId
        except AttributeError:
            return self._org_id
  
    @property
    def enterprise_orgUrl(self):
        '''Get the enterprise org url for this hub'''
        try:
            return self.org.properties.portalProperties.hub.settings.enterpriseOrg.portalHostname
        except AttributeError:
            return self.org.url
        
    @property
    def community_orgUrl(self):
        '''Get the community org url for this hub'''
        try:
            return self.org.properties.portalProperties.hub.settings.communityOrg.portalHostname
        except AttributeError:
            return self.org.url
    
    @_lazy_property
    def initiatives(self):
        return InitiativeManager(self)
    
    @_lazy_property
    def events(self):
        return EventManager(self)
    
class Initiative(collections.OrderedDict):
    """Represents an initiative"""
    
    def __init__(self, org, initiativeItem):
        '''Constructs an empty Initiative object'''
        if 'hubInitiative' not in initiativeItem.typeKeywords:
            raise TypeError("Item is not a valid initiative.")
        self.item = initiativeItem
        self._org = org
        self._initiativedict = self.item.get_data()
        pmap = PropertyMap(self._initiativedict)
        self.definition = pmap
            
    def __repr__(self):
        return '<%s title:"%s" owner:%s>' % (type(self).__name__, self.title, self.owner)
       
    @property
    def itemId(self):
        return self.item.id
    
    @property
    def title(self):
        return self.item.title
    
    @property
    def owner(self):
        return self.item.owner
    
    @property
    def url(self):
        return self.item.properties['url']
    
    @property
    def siteUrl(self):
        return self.item.url
    
    @_lazy_property
    def indicators(self):
        return IndicatorManager(self._org, self.item)
    
    def delete(self, force=False, dry_run=False):
        '''Deletes an initiative'''
        if self.item is not None:
            #Fetch Initiative Collaboration group
            _collab_groupId = self.item.properties['groupId']
            _collab_group = self._org.groups.get(_collab_groupId)
            #Fetch Open Data Group
            _od_groupId = self.item.properties['openDataGroupId']
            _od_group = self._org.groups.get(_od_groupId)
            #Disable delete protection on groups
            _collab_group.protected = False
            _od_group.protected = False
            #Delete groups and initiative
            _collab_group.delete()
            _od_group.delete()
            return self.item.delete(force, dry_run)
    
    def update(self, initiative_properties=None, data=None, thumbnail=None, metadata=None):
        '''Update an initiative'''
        if initiative_properties:
            return self.item.update(initiative_properties, data, thumbnail, metadata)          
    
class InitiativeManager(object):
    """Helper class for managing initiatives within a Hub"""
    
    def __init__(self, hub, initiative=None):
        self._org = hub.org
        self._enterprise_orgUrl = hub.enterprise_orgUrl
        if initiative:
            self._initiative = initiative
          
    def add(self, title, description=None, data=None, thumbnail=None):
        '''Adding an initiative'''
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
        od_group = self._org.groups.create_from_dict(_od_group_dict)
        collab_group = self._org.groups.create_from_dict(_collab_group_dict)
        
        #Protect groups from accidental deletion
        od_group.protected = True
        collab_group.protected = True
        
        #Adding it to _item_dict
        if od_group is not None and collab_group is not None:
            _item_dict['properties']['groupId'] = collab_group.id
            _item_dict['properties']['openDataGroupId'] = od_group.id
        
        #Create initiative and share it with collaboration group
        item = self._org.content.add(_item_dict, owner=self._org.users.me.username)
        item.share(groups=[collab_group])
        
        #update initiative data
        _item_data = {"assets": [{"id": "bannerImage","url": self._enterprise_orgUrl+"/sharing/rest/content/items/"+item.id+"/resources/detail-image.jpg","properties": {"type": "resource","fileName": "detail-image.jpg","mimeType": "image/jepg"},"license": {"type": "none"},"display": {"position": {"x": "center","y": "center"}}},{"id": "iconDark","url": self._enterprise_orgUrl+"/sharing/rest/content/items/"+item.id+"/resources/icon-dark.png","properties": {"type": "resource","fileName": "icon-dark.png","mimeType": "image/png"},"license": {"type": "none"}},{"id": "iconLight","url": self._enterprise_orgUrl+"/sharing/rest/content/items/"+item.id+"/resources/icon-light.png","properties": {"type": "resource","fileName": "icon-light.png","mimeType": "image/png"},"license": {"type": "none"}}],"steps": [{"id": "informTools","title": "Inform the Public","description": "Share data about your initiative with the public so people can easily find, download and use your data in different formats.","templateIds": [],"itemIds": []},{"id": "listenTools","title": "Listen to the Public","description": "Create ways to gather citizen feedback to help inform your city officials.","templateIds": [],"itemIds": []},{"id": "monitorTools","title": "Monitor Progress","description": "Establish performance measures that incorporate the publics perspective.","templateIds": [],"itemIds": []}],"indicators": [],"values": {"collaborationGroupId": collab_group.id,"openDataGroupId": od_group.id,"followerGroups": [],"bannerImage": {"source": "bannerImage","display": {"position": {"x": "center","y": "center"}}}}}
        _data = json.dumps(_item_data)
        item.update(item_properties={'text': _data})
        return Initiative(self._org, item)
    
    def get(self, initiative_id):
        '''Fetch initiative for given initiative id'''
        initiativeItem = self._org.content.get(initiative_id)
        if 'hubInitiative' in initiativeItem.typeKeywords:
            return Initiative(self._org, initiativeItem)
        else:
            raise TypeError("Item is not a valid initiative or is inaccessible.")
    
    def search(self, initiative_id=None, title=None, owner=None, created=None, modified=None, tags=None):
        '''Search for initiative'''
        initiativelist = []
        query = 'typekeywords:hubInitiative'
        if initiative_id!=None:
            query += ' AND id:'+initiative_id
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
        items = self._org.content.search(query=query, max_items=5000)
        for item in items:
            initiativelist.append(Initiative(self._org, item))
        return initiativelist
        
class Indicator(collections.OrderedDict):
    """Represents an indicator within an initiative"""
    
    def __init__(self, initiativeItem, indicatorObject):
        '''Constructs an empty Indicator object'''
        self._initiativeItem = initiativeItem
        self._initiativedata = self._initiativeItem.get_data()
        self._indicatordict = indicatorObject
        pmap = PropertyMap(self._indicatordict)
        self.definition = pmap
            
    def __repr__(self):
        return '<%s id:"%s" optional:%s>' % (type(self).__name__, self.indicatorId, self.optional)
       
    @property
    def indicatorId(self):
        return self._indicatordict['id']
    
    @property
    def indicatorType(self):
        return self._indicatordict['type']
    
    @property
    def optional(self):
        return self._indicatordict['optional']
    
    @property
    def url(self):
        try:
            return self._indicatordict['source']['url']
        except:
            return 'Url not available for this indicator'
        
    @property
    def name(self):
        try:
            return self._indicatordict['source']['url']
        except:
            return 'Name not available for this indicator'
        
    @property
    def itemId(self):
        try:
            return self._indicatordict['source']['itemId']
        except:
            return 'Item Id not available for this indicator'
        
    @property
    def mappings(self):
        try:
            return self._indicatordict['source']['mappings']
        except:
            return 'Attribute mapping not available for this indicator'
    
    def delete(self):
        '''Deletes an indicator from the initiative'''
        if self._indicatordict is not None:
            _indicator_id = self._indicatordict['id']
            self._initiativedata['indicators'] = list(filter(lambda indicator: indicator.get('id')!=_indicator_id, self._initiativedata['indicators']))
            _new_initiativedata = json.dumps(self._initiativedata)
            return self._initiativeItem.update(item_properties={'text': _new_initiativedata})
     
    def get_data(self):
        '''Retrieves the data associated with this indicator'''
        return self.definition
    
    def update(self, indicator_properties=None):
        '''Updates specified properties of an indicator'''
        try:
            _indicatorId = indicator_properties['id']
        except:
            return 'Indicator properties must include id of indicator'
        if indicator_properties is not None:
            self._initiativedata['indicators'] = [indicator_properties if indicator['id']==_indicatorId else indicator for indicator in self._initiativedata['indicators']]
            _new_initiativedata = json.dumps(self._initiativedata)
            status = self._initiativeItem.update(item_properties={'text': _new_initiativedata})      
            if status:
                self.definition = PropertyMap(indicator_properties)
                return status
    
class IndicatorManager(object):
    """Helper class for managing indicators within an initiative"""
    def __init__(self, org, initiativeItem):
        self._org = org
        self._initiativeItem = initiativeItem
        self._initiativedata = self._initiativeItem.get_data()
        self._indicators = self._initiativedata['indicators']
        
    def add(self, indicator_properties):
        '''Adds a new indicator to given initiative'''
        _stemplates = []
        _id = indicator_properties['id']
        _added = False
        
        #Fetch initiative template data
        _itemplateid = self._initiativedata['source']
        _itemplate = self._org.content.get(_itemplateid)
        _itemplatedata = _itemplate.get_data()
        
        #Fetch solution templates associated with initiative template
        for step in _itemplatedata['steps']:
            for _stemplateid in step['templateIds']:
                _stemplates.append(_stemplateid)
        
        #Fetch data for each solution template
        for _stemplateid in _stemplates:
            _stemplate = self._org.content.get(_stemplateid)
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
        '''Fetch initiative for given initiative id'''
        for indicator in self._indicators:
            if indicator['id']==indicator_id:
                return Indicator(self._initiativeItem, indicator)
        #raise CustomException
        return None
    
    def search(self, indicator_id=None, url=None, itemId=None, name=None):
        '''Search for indicator'''
        _indicators = []
        indicatorlist = []
        for indicator in self._indicators:
            _indicators.append(indicator)
        if indicator_id!=None:
            _indicators = [indicator for indicator in _indicators if indicator['id']==indicator_id]
        if url!=None:
            _indicators = [indicator for indicator in _indicators if indicator['source']['url']==url]
        if itemId!=None:
            _indicators = [indicator for indicator in _indicators if indicator['source']['itemId']==itemId]
        if name!=None:
            _indicators = [indicator for indicator in _indicators if indicator['source']['name']==name]
        for indicator in _indicators:
            indicatorlist.append(Indicator(self._initiativeItem, indicator))
        return indicatorlist

class Event(collections.OrderedDict):
    """Represents an event in a Hub"""
    def __init__(self, org, eventObject):
        '''Constructs an empty Event object'''
        self._org = org
        self._eventgeometry = eventObject.geometry
        self._eventdict = eventObject.attributes
        pmap = PropertyMap(self._eventdict)
        self.definition = pmap
            
    def __repr__(self):
        return '<%s title:"%s" location:%s>' % (type(self).__name__, self.title, self.location)
    
    @property
    def title(self):
        return self._eventdict['title']
    
    @property
    def location(self):
        return self._eventdict['location'] 
    
    @property
    def initiativeId(self):
        return self._eventdict['initiativeId'] 
    
    @property
    def siteId(self):
        return self._eventdict['siteId']
    
    @property
    def organizerName(self):
        return self._eventdict['organizerName'] 
    
    @property
    def organizers(self):
        return self._eventdict['organizers']
    
    @property
    def description(self):
        return self._eventdict['description']
    
    @property
    def startDate(self):
        return self._eventdict['startDate']
    
    @property
    def endDate(self):
        return self._eventdict['endDate']
    
    @property
    def creator(self):
        return self._eventdict['Creator']
    
    @property
    def capacity(self):
        return self._eventdict['capacity']
    
    @property
    def attendance(self):
        return self._eventdict['attendance']
    
    @property
    def status(self):
        return self._eventdict['status']
    
    @property
    def isCancelled(self):
        return self._eventdict['isCancelled']
    
    @property
    def geometry(self):
        return self._eventgeometry
    
class EventManager(object):
    """Helper class for managing events"""
    def __init__(self, hub, event=None):
        self._org = hub.org
        if event:
            self._event = event
            
    def __all_events(self):
        '''Fetches all initiatives for particular hub'''
        events = []
        _events_layer = self._org.content.search(query="typekeywords:hubEventsLayer", max_items=5000)[0]
        _events_layer_url = _events_layer.url + '/0'
        _events_data = FeatureLayer(_events_layer_url).query().features
        for event in _events_data:
            events.append(Event(self._org, event))
        return events
    
    def search(self, initiative_id=None, title=None, location=None, organizerName=None):
        '''Search for events'''
        events = []
        events = self.__all_events()
        if initiative_id!=None:
            events = [event for event in events if initiative_id==event.initiativeId]
        if title!=None:
            events = [event for event in events if title in event.title]
        if location!=None:
            events = [event for event in events if location in event.location]
        if organizerName!=None:
            events = [event for event in events if organizerName==event.organizerName]
        return events
    
    def get_map(self):
        '''View all events on a map'''
        _events_layer = self._org.content.search(query="typekeywords:hubEventsLayer", max_items=5000)[0]
        event_map = self._org.map(zoomlevel=2)
        event_map.basemap = 'dark-gray'
        event_map.add_layer(_events_layer, {'title':'Event locations for this Hub','opacity':0.7})
        return event_map