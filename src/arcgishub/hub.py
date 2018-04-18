from arcgis.gis import *
import datetime, time
import requests
import json

class Hub:
    """
    Acceessing an individual hub and all that it contains

    """
    
    def __init__(self, url):
        self.url = url
       
        def _enterprise_org_id(self):
        '''Return the Enterprise Organization Id for this hub'''
        org = GIS(self.url)
        e_org_id = org.properties.portalProperties.hub.settings.enterpriseOrg.orgId
        return e_org_id
    
    def _format_date(self, date):
        '''Return date in M-D-Y -- H:M:S format'''
        epoch_time = str(date)[0: 10]
        return datetime.datetime.fromtimestamp(float(epoch_time)).strftime('%m-%d-%Y -- %H:%M:%S')
    
    def _days_between(self, d1, d2):
        '''Return number of days between two dates'''
        d1 = date(int(d1[6:10]), int(d1[0:2]), int(d1[3:5]))
        d2 = date(int(d2[6:10]), int(d2[0:2]), int(d2[3:5]))
        return (d2 - d1).days
    
    def _initiative_object(self, data):
        '''Build a list of the initiative object'''
        all_initiatives = []
        total = data['total']
        for i in range(total):
            tags = []
            initiative = {}
            path = data['results'][i]
            initiative['id'] = path['id']
            initiative['owner'] = path['owner']
            initiative['created'] = self._format_date(path['created'])
            initiative['modified'] = self._format_date(path['modified'])
            initiative['title'] = path['title']
            initiative['description'] = path['description']
            initiative['url'] = path['url']
            try:
                tags = [path['tags'][j] for j in range(len(path['tags']))]
            except:
                pass
            initiative['tags'] = tags
            all_initiatives.append(initiative)
        return all_initiatives
    
    def _event_object(self, data):
        '''Build a list of the event object'''
        all_events = []
        total = len(data['features'])
        for i in range(total):
            event = {}
            path = data['features'][i]['attributes']
            event['title'] = path['title']
            event['location'] = path['location']
            event['description'] = path['description']
            event['startDate'] = self._format_date(path['startDate'])
            event['endDate'] = self._format_date(path['endDate'])
            event['organizerName'] = path['organizerName']
            event['capacity'] = path['capacity']
            event['attendance'] = path['attendance']
            event['status'] = path['status']
            event['isCancelled'] = path['isCancelled']
            event['siteId'] = path['siteId']
            event['initiativeId'] = path['initiativeId']
            try:
                event['geometry'] = data['features'][i]['geometry']
            except:
                pass
            all_events.append(event)
        return all_events
    
    def _temp_description(self,initiative):
        '''Return a dictionary with title and description of a particular event'''
        temp = {}
        temp['title'] = initiative['title']
        temp['description'] = initiative['description']
        return temp
            
    def initiatives(self):
        '''Extract all initiatives for this Hub and return the response json'''
        e_org_id = self._enterprise_org_id()
        request_url = 'https://www.arcgis.com/sharing/rest/search?q=typekeywords:hubInitiative%20AND%20orgid:'+e_org_id+'&f=json&num=100'
        response = requests.get(request_url)
        data = response.json()
        all_initiatives = self._initiative_object(data)
        return all_initiatives

    def initiative_names(self):
        '''Extract a list of all Initiative names from within this Hub'''
        initiatives = self.initiatives()
        count = len(initiatives)
        names = [initiatives[i]['title'] for i in range(count)]
        return names
    
    def initiative_ids(self):
        '''Extract a list of all Initiative ids from within this Hub'''
        initiatives = self.initiatives()
        count = len(initiatives)
        ids = [initiatives[i]['id'] for i in range(count)]
        return ids
    
    def initiative_description(self, name=None):
        '''Return the description of the requested initiative, or for all of them'''
        initiatives = self.initiatives()
        result = []
        if isinstance(name, str):
            for i in range(len(initiatives)):
                if name in initiatives[i]['title']:
                    result.append(self._temp_description(initiatives[i]))
        elif name==None:
            for i in range(len(initiatives)):
                result.append(self._temp_description(initiatives[i]))
        return result
    
    def initiative_search(self, name=None, location=None, created=None, modified=None, tags=None):
        '''Search for initiatives within Hubs based on certain parameters'''
        initiatives = self.initiatives()
        result = []
        now = datetime.datetime.now().strftime('%m-%d-%Y -- %H:%M:%S')
        for i in range(len(initiatives)):
            if name!=None:
                if name in initiatives[i]['title']:
                    result.append(initiatives[i])
            if created!=None:
                diff_days = self._days_between(initiatives[i]['created'], now)
                if created>=diff_days:
                    result.append(initiatives[i])
            if modified!=None:
                diff_days = self._days_between(initiatives[i]['modified'], now)
                if modified>=diff_days:
                    result.append(initiatives[i])
            if initiatives[i]['tags']==tags:
                result.append(initiatives[i])
        return result
    
    def events(self):
        '''Extract all events for this Hub and return the response json'''
        e_org_id = self._enterprise_org_id()
        request_url = 'https://www.arcgis.com/sharing/rest/search?q=typekeywords:hubEventsLayer View Service AND orgid:'+e_org_id+'&f=json&num=100'
        response = requests.get(request_url)
        data = response.json()
        events_layer = data['results'][0]['url']
        events_url = events_layer + '/0/query?where=1=1&f=json&outFields=*&returnGeometry=true'
        response = requests.get(events_url)
        events_data = response.json()
        all_events = self._event_object(events_data)
        return all_events 
    
    def event_names(self):
        '''Extract a list of all Event names from within this Hub'''
        data = self.events()
        count = len(data)
        names = [data[i]['title'] for i in range(count)]
        return names
    
    def event_description(self, name=None):
        '''Return the description of the requested event, or for all of them'''
        events = self.events()
        result = []
        if isinstance(name, str):
            for i in range(len(events)):
                if name in events[i]['title']:
                    result.append(self._temp_description(events[i]))
        elif name==None:
            for i in range(len(events)):
                result.append(self._temp_description(events[i]))
        return result