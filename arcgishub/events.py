from arcgis._impl.common._mixins import PropertyMap
from collections import OrderedDict
from arcgis.geocoding import geocode
import json

class Event(OrderedDict):
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
        self._hub = self._gis.hub
        self._eventdict = eventObject['attributes']
        try:
            self._eventdict['geometry'] = eventObject['geometry']
        except KeyError:
            self._eventdict['geometry'] = {'x':0.00, 'y':0.00}
        pmap = PropertyMap(self._eventdict)
        self.definition = pmap
            
    def __repr__(self):
        return '<%s title:"%s" venue:%s>' % (
            type(self).__name__, 
            self.title, 
            self.venue
        )
    
    @property 
    def event_id(self):
        """
        Returns the unique identifier of the event
        """
        return self._eventdict['OBJECTID']

    @property
    def title(self):
        """
        Returns the title of the event
        """
        return self._eventdict['title']
    
    @property
    def venue(self):
        """
        Returns the location of the event
        """
        return self._eventdict['venue']

    @property
    def address(self):
        """
        Returns the street address for the venue of the event
        """
        return self._eventdict['address1'] 
    
    @property
    def initiative_id(self):
        """
        Returns the initiative id of the initiative the event belongs to
        """
        return self._eventdict['initiativeId'] 
    
    @property
    def organizers(self):
        """
        Returns the name and email of the event organizers
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
    def access(self):
        """
        Returns access permissions of the event
        """
        return self._eventdict['status']

    @property 
    def group_id(self):
        """
        Returns groupId for the event
        """
        return self._eventdict['groupId']

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
        return self._eventdict['geometry']

    def delete(self):
        """
        Deletes an event
        
        :return:
            A bool containing True (for success) or False (for failure). 
        
        .. code-block:: python
        
            USAGE EXAMPLE: Delete an event successfully
        
            event1 = myhub.events.get(24)
            event1.delete()
        
            >> True
        """
        _group = self._gis.groups.get(self.group_id)
        _group.protected = False
        _group.delete()
        params = {'f': 'json', 'objectIds': self.event_id, 'token': self._gis._con.token}
        delete_event = self._gis._con.post(path='https://hub.arcgis.com/api/v3/events/'+self._hub.enterprise_org_id+'/Hub Events/FeatureServer/0/deleteFeatures', postdata=params)
        return delete_event['deleteResults'][0]['success']
        
    def update(self, event_properties):
        """
        Updates properties of an event
        
        :return:
            A bool containing True (for success) or False (for failure). 
        
        .. code-block:: python
        
            USAGE EXAMPLE: Update an event successfully
        
            event1 = myhub.events.get(id)
            event_properties = {'status': 'planned', description: 'Test'}
            event1.update(event_properties)
        
            >> True
        """
        _feature = {}

        #Build event feature 
        event_properties['OBJECTID'] = self.event_id
        _feature["attributes"] = self._eventdict
        for key,value in event_properties.items():
            _feature["attributes"][key] = value
        _feature["geometry"] = self.geometry
        event_data = [_feature]

        #Update event
        url = 'https://hub.arcgis.com/api/v3/events/'+self._hub.enterprise_org_id+'/Hub Events/FeatureServer/0/updateFeatures'
        params = {
            'f': 'json', 
            'features': event_data,
            'token': self._gis._con.token
        }
        update_event = self._gis._con.post(path=url, postdata=params)
        return update_event['updateResults'][0]['success']

class EventManager(object):
    """Helper class for managing events within a Hub. This class is not created by users directly. 
    An instance of this class, called 'events', is available as a property of the Hub object. Users
    call methods on this 'events' object to manipulate (add, search, get_map etc) events 
    of a particular Hub. 
    """
    def __init__(self, hub, event=None):
        self._hub = hub
        self._gis = self._hub.gis
        if event:
            self._event = event
            
    def _all_events(self):
        """
        Fetches all events for particular hub.
        """
        events = []
        url = 'https://hub.arcgis.com/api/v3/events/'+self._hub.enterprise_org_id+'/Hub Events/FeatureServer/0/query'
        params = {
            'f' :'json', 
            'outFields': '*', 
            'where': '1=1',
            'token': self._gis._con.token
        }
        all_events = self._gis._con.get(url, params)
        _events_data = all_events['features']
        for event in _events_data:
            events.append(Event(self._gis, event))
        return events

    def add(self, event_properties):
        """
        Adds an event for an initiative.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        event_properties    Required dictionary. See table below for the keys and values.
        ===============     ====================================================================
        

        *Key:Value Dictionary Options for Argument event_properties*
        =================  =====================================================================
        **Key**            **Value**
        -----------------  ---------------------------------------------------------------------
        title              Required string. Name of event.
        -----------------  ---------------------------------------------------------------------
        description        Required string. Description of the event.
        -----------------  ---------------------------------------------------------------------
        initiaitve_id      Required string. Name label of the item.
        -----------------  ---------------------------------------------------------------------
        venue              Required string. Venue name for the event.
        -----------------  ---------------------------------------------------------------------
        address1           Required string. Street address for the venue.
        -----------------  ---------------------------------------------------------------------
        status             Required string. Access of event. Valid values are private, planned, 
                           public, draft.
        -----------------  ---------------------------------------------------------------------
        startDate          Required start date of the event in milliseconds since UNIX epoch.
        -----------------  ---------------------------------------------------------------------
        endDate            Required end date of the event in milliseconds since UNIX epoch.
        -----------------  ---------------------------------------------------------------------
        isAllDay           Required boolean. Indicates if the event is a day long event.
        -----------------  ---------------------------------------------------------------------
        capacity           Optional integer. The attendance capacity of the event venue.
        -----------------  ---------------------------------------------------------------------
        address2           Optional string.  Additional information about event venue street address.
        -----------------  ---------------------------------------------------------------------
        onlineLocation     Optional string. Web URL or other details for online event.
        -----------------  ---------------------------------------------------------------------
        organizers         Optional list of dictionary of keys `name` and `contact` for each organizer's 
                           name and email. Default values are name, email, username of event creator.
        -----------------  ---------------------------------------------------------------------
        sponsors           Optional list of dictionary of keys `name` and `contact` for each sponsor's 
                           name and contact.
        =================  =====================================================================

        :return:
            Event if successfully added.

        .. code-block:: python
            
            USAGE EXAMPLE: Add an event successfully
            
            event_properties = {
                'title':'Test Event',
                'description': 'Testing with python',
                'initiativeId': '43f..',
                'venue': 'Washington Monument',
                'address1': '2 15th St NW, Washington, District of Columbia, 20024',
                'status': 'planned',
                'startDate': 1562803200,
                'endDate': 1562889600,
                'isAllDay': 1
            }
            
            new_event = myhub.events.add(event_properties)
        """
        _feature = {}
        #Fetch initiaitve site id
        _initiative = self._hub.initiatives.get(event_properties['initiativeId'])
        event_properties['siteId'] = _initiative.site_id
        #Set organizers if not provided
        try:
            event_properties['organizers']
        except:
            _organizers_list = [
                {
                    "name":self._gis.users.me.fullName, 
                    "contact": self._gis.users.me.email, 
                    "username": self._gis.users.me.username
                }
            ]
            _organizers = json.dumps(_organizers_list)
            event_properties['organizers'] = _organizers
        #Set sponsors if not provided
        try:
            event_properties['sponsors']
            event_properties['sponsors'] = json.dumps(event_properties['sponsors'])
        except:
            _sponsors = []
            event_properties['sponsors'] = json.dumps(_sponsors)
        #Set onlineLocation if not provided
        try:
            event_properties['onlineLocation']
        except:
            _onlineLocation = ''
            event_properties['onlineLocation'] = _onlineLocation
        #Set geometry if not provided
        try:
            event_properties['geometry']
            geometry = event_properties['geometry']
            del event_properties['geometry']
        except:
            geometry = geocode(event_properties['address1'])[0]['location']

        event_properties['schemaVersion'] = 2
        event_properties['location'] = ''
        event_properties['url'] = event_properties['title'].replace(' ', '-').lower()
        
        #Generate event id for new event
        event_id = max([event.event_id for event in self._all_events()]) + 1
        
        #Create event group
        _event_group_dict = {
            'title': event_properties['title'], 
            'access': 'public', 
            'tags': ["Hub Event Group", "Open Data", "hubEvent|"+str(event_id)]
        }
        _event_group = self._gis.groups.create_from_dict(_event_group_dict)
        _event_group.protected = True
        event_properties['groupId'] = _event_group.id
        
        #Build new event feature and create it
        _feature["attributes"] = event_properties
        _feature["geometry"] = geometry
        event_data = [_feature]
        url = 'https://hub.arcgis.com/api/v3/events/'+self._hub.enterprise_org_id+'/Hub Events/FeatureServer/0/addFeatures'
        params = {
            'f': 'json', 
            'features': event_data,
            'token': self._gis._con.token
        }
        add_event = self._gis._con.post(path=url, postdata=params)
        try:
            add_event['addResults']
            return self.get(add_event['addResults'][0]['objectId'])
        except:
            return add_event

    def search(self, initiative_id=None, title=None, venue=None, organizer_name=None):
        """ 
        Searches for events within a Hub.
        
        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        initiative_id       Optional string. Initiative itemid.
        ---------------     --------------------------------------------------------------------
        title               Optional string. Title of the event.
        ---------------     --------------------------------------------------------------------
        venue               Optional string. Venue where event is held.
        ---------------     --------------------------------------------------------------------
        organizer_name      Optional string. Name of the organizer of the event.
        ===============     ====================================================================
        
        :return:
           A list of matching indicators.
        
        """
        events = []
        events = self._all_events()
        if initiative_id!=None:
            #events = 
            events = [event for event in events if initiative_id==event.initiative_id]
        if title!=None:
            events = [event for event in events if title in event.title]
        if venue!=None:
            events = [event for event in events if venue in event.venue]
        if organizer_name!=None:
            events = [event for event in events if organizer_name in event.organizers]
        return events

    def get(self, event_id):
        """ Get the event for the specified event_id.
        
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        event_id                   Required integer. The event identifier.
        =======================    =============================================================
        
        :return:
            The event object.
        
        """
        url = 'https://hub.arcgis.com/api/v3/events/'+self._hub.enterprise_org_id+'/Hub Events/FeatureServer/0/'+str(event_id)
        params = {'f':'json', 'token':self._gis._con.token}
        feature = self._gis._con.get(url, params)
        return Event(self._gis, feature['feature'])

    def get_map(self):
        """
        Plot all events for a Hub in an embedded webmap within the notebook.
        """
        _events_layer = self._gis.content.search(query="typekeywords:hubEventsLayer", max_items=5000)[0]
        event_map = self._gis.map(zoomlevel=2)
        event_map.basemap = 'dark-gray'
        event_map.add_layer(_events_layer, {'title':'Event locations for this Hub','opacity':0.7})
        return event_map