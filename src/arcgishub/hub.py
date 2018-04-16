from arcgis.gis import *
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
        #print(type(e_org_id))
        return e_org_id
    
    def get_all_initiatives(self):
        '''Extract all initiatives for this Hub and return the response json'''
        e_org_id = self._enterprise_org_id()
        request_url = 'https://www.arcgis.com/sharing/rest/search?q=typekeywords:hubInitiative%20AND%20orgid:'+e_org_id+'&f=json&num=100'
        response = requests.get(request_url)
        data = response.json()
        return data

    def initiative_names(self):
        '''Extract a list of all Initiative names from within this Hub'''
        data = self.get_all_initiatives()
        count = data['total']
        names = [data['results'][i]['title'] for i in range(0,count)]
        return names
    
    def initiative_ids(self):
        '''Extract a list of all Initiative ids from within this Hub'''
        data = self.get_all_initiatives()
        count = data['total']
        ids = [data['results'][i]['id'] for i in range(count)]
        return ids
    
    def get_all_events(self):
        '''Extract all events for this Hub and return the response json'''
        e_org_id = self._enterprise_org_id()
        request_url = 'https://www.arcgis.com/sharing/rest/search?q=typekeywords:hubEventsLayer View Service AND orgid:'+e_org_id+'&f=json&num=100'
        response = requests.get(request_url)
        data = response.json()
        events_layer = data['results'][0]['url']
        events_url = events_layer + '/0/query?where=1=1&f=json&outFields=*&returnGeometry=true'
        response = requests.get(events_url)
        events_data = response.json()
        return events_data 
    
    def event_names(self):
        '''Extract a list of all Event names from within this Hub'''
        data = self.get_all_events()
        count = len(data['fields'])
        names = [data['features'][i]['attributes']['title'] for i in range(count)]
        return names