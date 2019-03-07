from arcgis.gis import GIS
from arcgis.features import FeatureLayer
import json

class Hub(object):
    "Acceessing an individual hub and its events, indicators and initiatives"

    def __init__(self, url, username=None, password=None):
        self.url = url
        self._username = username
        self._password = password
        self._org = GIS(self.url, self._username, self._password)
    
    @property
    def orgs(self):
        '''Get both org urls for particular hub'''
        orglist = []
        orglist.append(self.url)
        try:
            companion_org_id = self.org.properties.portalProperties.hub.settings.communityOrg.portalHostname
        except AttributeError:
            companion_org_id = self.org.properties.portalProperties.hub.settings.enterpriseOrg.portalHostname
        orglist.append(companion_org_id)
        return orglist
    
    def _all_events(self):
        '''Fetches all initiatives for particular hub'''
        events = []
        _events_layer = self._org.content.search(query="typekeywords:hubEventsLayer", max_items=5000)[0]
        _events_layer_url = _events_layer.url + '/0'
        _events_data = FeatureLayer(_events_layer_url).query().features
        for event in _events_data:
            events.append(self._build_event_object(event))
        return events
     
    def _all_indicators(self, initiative_id):
        '''Fetches the indicators for given initiative'''
        _initiative = self.initiative_get(initiative_id)
        return _initiative.get_data()['indicators']
    
    def _build_event_object(self, eventdict):
        '''Builds event object'''
        event = {}
        _path = eventdict.attributes
        event['title'] = _path['title']
        event['location'] = _path['location']
        event['description'] = _path['description']
        event['startDate'] = _path['startDate']
        event['endDate'] = _path['endDate']
        event['organizerName'] = _path['organizerName']
        event['creator'] = _path['Creator']
        event['capacity'] = _path['capacity']
        event['attendance'] = _path['attendance']
        event['status'] = _path['status']
        event['isCancelled'] = _path['isCancelled']
        event['siteId'] = _path['siteId']
        event['initiativeId'] = _path['initiativeId']
        try:
            event['geometry'] = eventdict.geometry
        except:
            pass
        return event
        
    def _build_indicator_object(self, indicatordict):
        '''Builds indicator object'''
        indicator = {}
        indicator['id'] = indicatordict['id']
        try:
            path = indicatordict['source']
            indicator['url'] = path['url']
            indicator['itemId'] = path['itemId']
            indicator['name'] = path['name']
            if len(path['mappings'])!=0:
                indicator['mappings'] =  []
                for key in range(len(path['mappings'])):
                    _temp = {}
                    _temp["id"] = path['mappings'][key]['id']
                    _temp["name"] = path['mappings'][key]['name']
                    indicator['mappings'].append(_temp)
        except KeyError:
            pass
        return indicator

    def events_map(self):
        '''Visualize events for a hub in an embedded map'''
        _events_layer = self._org.content.search(query="typekeywords:hubEventsLayer", max_items=5000)[0]
        event_map = self._org.map(zoomlevel=2)
        event_map.basemap = 'dark-gray'
        event_map.add_layer(_events_layer, {'title':'Event locations for this Hub','opacity':0.7})
        return event_map
    
    def event_search(self, initiative_id=None, title=None, location=None, organizerName=None):
        '''Search for events'''
        events = []
        events = self._all_events()
        if initiative_id!=None:
            events = [event for event in events if event['initiativeId']==initiative_id]
        if title!=None:
            events = [event for event in events if event['title']==title]
        if location!=None:
            events = [event for event in events if location in event['location']]
        if organizerName!=None:
            events = [event for event in events if organizerName in event['organizerName']]
        return events
    
    def indicator_add(self, initiative_id, indicator_object):
        '''Adds a new indicator to given initiative'''
        initiative = self.initiative_get(initiative_id)
        data = initiative.get_data()
        data['indicators'].append(indicator_object)
        initiative_data = json.dumps(data)
        return initiative.update(item_properties={'text': initiative_data})
    
    def indicator_delete(self, initiative_id, indicator_id):
        '''Deletes a particular indicator for given initiative'''
        _invalid_indicator = False
        initiative = self.initiative_get(initiative_id)
        data = initiative.get_data()
        for indicator in data['indicators']:
            if indicator_id==indicator['id']:
                _invalid_indicator = True
                break
        if _invalid_indicator:
            data['indicators'] = list(filter(lambda indicator: indicator.get('id')!=indicator_id, data['indicators']))
            initiative_data = json.dumps(data)
            return initiative.update(item_properties={'text': initiative_data})
        else:
            return 'Indicator does not exist'
        
    def indicator_get(self, initiative_id, indicator_id):
        '''Fetch an indicator based on id'''
        indicators = self._all_indicators(initiative_id)
        try:
            for indicator in indicators:
                if indicator['id']==indicator_id:
                    return indicator
        except:
            return 'Indicator does not exist'
        
    def indicator_search(self, initiative_id, indicator_id=None, url=None, itemId=None, name=None):
        '''Search for indicator'''
        indicators = []
        temp = self._all_indicators(initiative_id)
        for indicator in temp:
            indicators.append(self._build_indicator_object(indicator))
        if indicator_id!=None:
            indicators = [indicator for indicator in indicators if indicator['id']==indicator_id]
        if url!=None:
            indicators = [indicator for indicator in indicators if indicator['url']==url]
        if itemId!=None:
            indicators = [indicator for indicator in indicators if indicator['itemId']==itemId]
        if name!=None:
            indicators = [indicator for indicator in indicators if indicator['name']==name]
        return indicators
    
    def initiative_add(self, initiative_properties, data=None, thumbnail=None, metadata=None, owner=None, folder=None):
        '''Adding a new initiative'''
        initiative_properties['typekeywords'] = "hubInitiative"
        return self._org.content.add(initiative_properties, data, thumbnail, metadata, owner, folder)
    
    def initiative_delete(self, initiative_id, force=False, dry_run=False):
        '''Deletes an initiative'''
        initiative = self.initiative_get(initiative_id)
        if initiative is not None:
            return initiative.delete(force, dry_run)
        else:
            return "Item is not a valid initiative or is inaccessible."
        
    def initiative_get(self, initiative_id):
        '''Fetch an initiative based on id'''
        initiative = self._org.content.get(initiative_id)
        if initiative is not None:
            if 'hubInitiative' not in initiative.typeKeywords:
                return "Item is not a valid initiative or is inaccessible."
            return initiative
        return None
    
    def initiative_search(self, initiative_id=None, title=None, owner=None, created=None, modified=None, tags=None):
        '''Search for initiative'''
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
        return self._org.content.search(query=query, max_items=5000)
    
    def initiative_update(self, initiative_id, initiative_properties=None, data=None, thumbnail=None, metadata=None):
        '''Update an initiative'''
        initiative = self.initiative_get(initiative_id)
        if initiative is not None:
            return initiative.update(initiative_properties, data, thumbnail, metadata)
        else:
            return "Item is not a valid initiative or is inaccessible."
