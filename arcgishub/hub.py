from arcgis.gis import GIS
from arcgis._impl.common._mixins import PropertyMap
import collections

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
        self._initiative = None
        self.org = GIS(self.url, self._username, self._password)
        
    def _org_id(self):
        '''Return the Organization Id for this hub'''
        try:
            _org_id = self.org.properties.id
            return _org_id
        except AttributeError:
            return "Invalid Hub"
            sys.exit(0)
        
    @property
    def orgs(self):
        '''Get both org urls for this hub'''
        orglist = []
        orglist.append(self.org.url)
        try:
            companion_org_id = self.org.properties.portalProperties.hub.settings.communityOrg.portalHostname
        except AttributeError:
            companion_org_id = self.org.properties.portalProperties.hub.settings.enterpriseOrg.portalHostname
        orglist.append(companion_org_id)
        return orglist
    
    @_lazy_property
    def initiatives(self):
        return InitiativeManager(self)
    
    @_lazy_property
    def event(self):
        return EventManager(self)
    
class Initiative(collections.OrderedDict):
    """Represents an initiative"""
    
    def __init__(self, org, initiativeItem=None):
        '''Constructs an empty Initiative object'''
        if initiativeItem:
            if 'hubInitiative' not in initiativeItem.typeKeywords:
                raise TypeError("Item is not a valid initiative.")
            self.item = initiativeItem
            self._org = org
            self._initiativedict = self.item.get_data()
            pmap = PropertyMap(self._initiativedict)
            self.definition = pmap
        else:
            self.item = None
            self._org = org
            self._initiativedict = {"type":"Hub Initiative", "typekeywords":"hubInitiative"}
            pmap = PropertyMap(self._initiativedict)
            self.definition = pmap
            
    def __repr__(self):
        return '<%s title:"%s" owner:%s>' % (type(self).__name__, self.initiativeTitle, self.initiativeOwner)
       
    @property
    def initiativeId(self):
        return self.item.id
    
    @property
    def initiativeTitle(self):
        return self.item.title
    
    @property
    def initiativeOwner(self):
        return self.item.owner
    
    def delete(self, force=False, dry_run=False):
        '''Deletes an initiative''' 
        if self.item is not None:
            return self.item.delete(force, dry_run)
    
    def update(self, initiative_properties=None, data=None, thumbnail=None, metadata=None):
        '''Update an initiative'''
        if initiative_properties:
            return self.item.update(initiative_properties, data, thumbnail, metadata)
    
class InitiativeManager(object):
    """Helper class for managing initiatives within a Hub"""
    
    def __init__(self, hub, initiative=None):
        self._org = hub.org
        if initiative:
            self._initiative = initiative
        
    @_lazy_property
    def indicators(self):
        return IndicatorManager(self)
          
    def add(self, initiative_properties, data=None, thumbnail=None, metadata=None, owner=None, folder=None):
        '''Adding an initiative'''
        initiative_properties['typekeywords'] = "hubInitiative"
        item = self._org.content.add(initiative_properties, data, thumbnail, metadata, owner, folder)
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