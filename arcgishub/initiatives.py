from collections import OrderedDict
from arcgishub.indicators import Indicator, IndicatorManager
from arcgishub.utils import _lazy_property
from arcgishub import hub

class Initiative(OrderedDict):
    """
    Represents an initiative within a Hub. An Initiative supports 
    policy- or activity-oriented goals through workflows, tools and team collaboration.
    """
    
    def __init__(self, hub, initiativeItem):
        """
        Constructs an empty Initiative object
        """
        self.item = initiativeItem
        self._hub = hub
        self._gis = self._hub.gis
        #self._gis = gis
        #self._hub = gis.hub
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
    def initiative_url(self):
        """
        Returns the url of the initiative editor
        """
        return self.item.properties['url']

    @property 
    def site_id(self):
        """
        Returns the itemid of the initiative site
        """
        try:
            return self.item.properties['siteId']
        except:
            return self._initiativedict['steps'][0]['itemIds'][0]

    @property
    def site_url(self):
        """
        Getter/Setter for the url of the initiative site
        """
        return self.sites.get(self.site_id).url

    @site_url.setter
    def site_url(self, value):
        self.item.url = value
    
    @property
    def content_group_id(self):
        """
        Returns the groupId for the content group
        """
        return self.item.properties['contentGroupId']
    
    @property
    def collab_group_id(self):
        """
        Returns the groupId for the collaboration group
        """
        return self.item.properties['collaborationGroupId']

    @property
    def followers_group_id(self):
        """
        Returns the groupId for the followers group
        """
        return self.item.properties['followersGroupId']
    
    @_lazy_property
    def indicators(self):
        """
        The resource manager for an Initiative's indicators. 
        See :class:`~hub.hub.IndicatorManager`.
        """
        return IndicatorManager(self._gis, self.item)

    @_lazy_property
    def sites(self):
        """
        The resource manager for an Initiative's sites. 
        See :class:`~hub.sites.SiteManager`.
        """
        return SiteManager(self._hub, self)

    @_lazy_property
    def all_events(self):
        """
        Fetches all events (past or future) pertaining to an initiative
        """
        return self._hub.events.search(initiative_id=self.item.id)
    
    @_lazy_property
    def followers(self, community_gis=None):
        """
        Fetches the list of followers for initiative. 
        """
        followers = []
        _email = False
        _users_e = self._gis.users.search(query='hubInitiativeId|'+self.itemid, outside_org=True)
        if community_gis is not None:
            _users_c = community_gis.users.search(query='hubInitiativeId|'+self.itemid, outside_org=True)
            _email = True
        for _user in _users_e:
            _temp = {}
            _temp['name'] = _user.fullName
            _temp['username'] = _user.username
            if _email:
                try:
                    _temp['email'] = _user.email
                except AttributeError:
                    for _user_c in _users_c:
                        if _user_c.username==_user.username:
                            try:
                                _temp['email'] = _user_c.email
                            except AttributeError:
                                pass
            followers.append(_temp)
        return followers

    def add_content(self, items_list):
        """
        Adds a batch of items to the initiative content library.
        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        items_list                Required list. A list of Item or item ids to add to the initiative
        =====================     ====================================================================
        """
        #Fetch Initiative Collaboration group
        _collab_group = self._gis.groups.get(self.collab_group_id)
        #Fetch Content Group
        _content_group = self._gis.groups.get(self.content_group_id)
        #share items with groups
        return self._gis.content.share_items(items_list, groups=[_collab_group, _content_group])

    def delete(self):
        """
        Deletes the initiative and its site. 
        If unable to delete, raises a RuntimeException.
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
            _collab_group = self._gis.groups.get(self.collab_group_id)
            #Fetch Content Group
            _content_group = self._gis.groups.get(self.content_group_id)
            #Fetch Followers Group
            _followers_group = self._gis.groups.get(self.followers_group_id)
            #Fetch initiative site
            try:
                _site = self._hub.sites.get(self.site_id)
                _site.protected = False
                _site.delete()
            except:
                pass
            #Disable delete protection on groups and site
            try:
                _collab_group.protected = False
                _content_group.protected = False
                _followers_group.protected = False
            except:
                pass
            #Delete groups, site and initiative
            _collab_group.delete()
            _content_group.delete()
            _followers_group.delete()
            return self.item.delete()

    def reassign_to(self, target_owner):
        """
        Allows the administrator to reassign the initiative object from one 
        user to another. 
        .. note::
            This will transfer ownership of all items (site, content) and groups that
            belong to this initiative to the new target_owner.
        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        target_owner              Required string. The new desired owner of the initiative.
        =====================     ====================================================================
        """
        ###check if admin user is performing this action
        if 'admin' not in self._gis.users.me.role:
            return Exception("You do not have the administrator privileges to perform this action.")
        #fetch the core team for this initiative
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
        #fetch content and followers teams
        content_team = self._gis.groups.get(self.content_group_id)
        followers_team = self._gis.groups.get(self.followers_group_id)
        #reassign them to target_owner
        content_team.reassign_to(target_owner)
        followers_team.reassign_to(target_owner)
        core_team.reassign_to(target_owner)
        return self._gis.content.get(self.itemid)

    def share(self, everyone=False, org=False, groups=None, allow_members_to_edit=False):
        """
        Shares an initiative and associated site with the specified list of groups.
        ======================  ========================================================
        **Argument**            **Description**
        ----------------------  --------------------------------------------------------
        everyone                Optional boolean. Default is False, don't share with
                                everyone.
        ----------------------  --------------------------------------------------------
        org                     Optional boolean. Default is False, don't share with
                                the organization.
        ----------------------  --------------------------------------------------------
        groups                  Optional list of group ids as strings, or a list of
                                arcgis.gis.Group objects, or a comma-separated list of
                                group IDs.
        ----------------------  --------------------------------------------------------
        allow_members_to_edit   Optional boolean. Default is False, to allow item to be
                                shared with groups that allow shared update
        ======================  ========================================================
        :return:
            A dictionary with key "notSharedWith" containing array of groups with which the items could not be shared.
        """
        site = self._hub.sites.get(self.site_id)
        result1 = site.item.share(everyone=everyone, org=org, groups=groups, allow_members_to_edit=allow_members_to_edit)
        result2 = self.item.share(everyone=everyone, org=org, groups=groups, allow_members_to_edit=allow_members_to_edit)
        print(result1)
        return result2

    def unshare(self, groups):
        """
        Stops sharing of the initiative and its associated site with the specified list of groups.
        ================  =========================================================================================
        **Argument**      **Description**
        ----------------  -----------------------------------------------------------------------------------------
        groups            Optional list of group names as strings, or a list of arcgis.gis.Group objects,
                          or a comma-separated list of group IDs.
        ================  =========================================================================================
        :return:
            Dictionary with key "notUnsharedFrom" containing array of groups from which the items could not be unshared.
        """
        site = self._hub.sites.get(self.site_id)
        result1 = site.item.unshare(groups=groups)
        result2 = self.item.unshare(groups=groups)
        print(result1)
        return result2


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
                if key=='title':
                    title = value
                    #Fetch Initiative Collaboration group
                    _collab_group = self._gis.groups.get(self.collab_group_id)
                    #Fetch Content Group
                    _content_group = self._gis.groups.get(self.content_group_id)
                    #Fetch Followers Group
                    _followers_group = self._gis.groups.get(self.followers_group_id)
                    #Update title for all groups
                    _collab_group.update(title=title+' Core Team')
                    _content_group.update(title=title+' Content')
                    _followers_group.update(title=title+' Followers')
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
          
    def add(self, title, description=None, site=None, data=None, thumbnail=None):
        """ 
        Adds a new initiative to the Hub.
        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        title               Required string.
        ---------------     --------------------------------------------------------------------
        description         Optional string. 
        ---------------     --------------------------------------------------------------------
        site                Optional Site object. 
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
            description = 'Create your own initiative by combining existing applications with a custom site.'
        _snippet = "Create your own initiative by combining existing applications with a custom site. Use this initiative to form teams around a problem and invite your community to participate."
        _item_dict = {"type":"Hub Initiative", "snippet":_snippet, "typekeywords":"Hub, hubInitiative, OpenData", "title":title, "description": description, "licenseInfo": "CC-BY-SA","culture": "{{culture}}", "properties":{}}
        
        #Defining content, collaboration and followers groups
        _content_group_title = title + ' Content'
        _content_group_dict = {"title": _content_group_title, "tags": ["Hub Group", "Hub Content Group", "Hub Site Group", "Hub Initiative Group"], "access":"public"}
        _collab_group_title = title + ' Core Team'
        _collab_group_dict = {"title": _collab_group_title, "tags": ["Hub Group", "Hub Initiative Group", "Hub Site Group", "Hub Core Team Group", "Hub Team Group"], "access":"org"}
        _followers_group_title = title + ' Followers'
        _followers_group_dict = {"title": _followers_group_title, "tags": ["Hub Initiative Group", " Hub Initiative Followers Group", "Hub Initiative Group"], "access":"public"}
        
        #Create groups
        content_group =  self._gis.groups.create_from_dict(_content_group_dict)
        collab_group =  self._gis.groups.create_from_dict(_collab_group_dict)
        followers_group = self._gis.groups.create_from_dict(_followers_group_dict)
        
        #Protect groups from accidental deletion
        content_group.protected = True
        collab_group.protected = True
        followers_group.protected = True
        
        #Adding it to _item_dict
        if content_group is not None and collab_group is not None and followers_group is not None:
            _item_dict['properties']['collaborationGroupId'] = collab_group.id
            _item_dict['properties']['contentGroupId'] = content_group.id
            _item_dict['properties']['followersGroupId'] = followers_group.id
        
        #Create initiative and share it with collaboration group
        item =  self._gis.content.add(_item_dict, owner=self._gis.users.me.username)
        item.share(groups=[collab_group])

        #Create initiative site and set initiative properties
        _initiative = Initiative(self._hub, item)
        if site is None:
            site = _initiative.sites.add(title=title)
        else:
            site = _initiative.sites.clone(site, pages=True, title=title)
        item.update(item_properties={'url': site.url, 'culture': self._gis.properties.user.culture})
        _initiative.site_url = site.item.url
        item.properties['site_id'] = site.itemid
        
        #update initiative data
        _item_data = {"assets": [{"id": "bannerImage","url": self._hub.enterprise_org_url+"/sharing/rest/content/items/"+item.id+"/resources/detail-image.jpg","properties": {"type": "resource","fileName": "detail-image.jpg","mimeType": "image/jepg"},"license": {"type": "none"},"display": {"position": {"x": "center","y": "center"}}},{"id": "iconDark","url": self._hub.enterprise_org_url+"/sharing/rest/content/items/"+item.id+"/resources/icon-dark.png","properties": {"type": "resource","fileName": "icon-dark.png","mimeType": "image/png"},"license": {"type": "none"}},{"id": "iconLight","url": self._hub.enterprise_org_url+"/sharing/rest/content/items/"+item.id+"/resources/icon-light.png","properties": {"type": "resource","fileName": "icon-light.png","mimeType": "image/png"},"license": {"type": "none"}}],"steps": [{"id": "informTools","title": "Inform the Public","description": "Share data about your initiative with the public so people can easily find, download and use your data in different formats.","templateIds": [],"itemIds": [site.itemid]},{"id": "listenTools","title": "Listen to the Public","description": "Create ways to gather citizen feedback to help inform your city officials.","templateIds": [],"itemIds": []},{"id": "monitorTools","title": "Monitor Progress","description": "Establish performance measures that incorporate the publics perspective.","templateIds": [],"itemIds": []}],"indicators": [],"values": {"collaborationGroupId": collab_group.id,"contentGroupId": content_group.id,"followersGroupId": followers_group.id,"bannerImage": {"source": "bannerImage","display": {"position": {"x": "center","y": "center"}}}}}
        _data = json.dumps(_item_data)
        item.update(item_properties={'text': _data})
        return Initiative(self._hub, item)

    def clone(self, initiative, origin_hub=None, title=None):
        """
        Clone allows for the creation of an initiative that is derived from the current initiative.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        initiative          Required Initiative object of initiative to be cloned.
        ---------------     --------------------------------------------------------------------
        origin_hub          Optional Hub object. Required only for cross-org clones where the 
                            initiative being cloned is not an item with public access.
        ---------------     --------------------------------------------------------------------
        title               Optional String.
        ===============     ====================================================================
        :return:
           Initiative.
        """
        from datetime import timezone
        now = datetime.now(timezone.utc)
        #Checking if item of correct type has been passed 
        if 'hubInitiative' not in initiative.item.typeKeywords:
            raise Exception("Incorrect item type. Initiative item needed for cloning.")
        #New title
        if title is None:
            title = initiative.title + "-copy-%s" % int(now.timestamp() * 1000)
        #If cloning within same org
        if origin_hub is None:
            origin_hub = self._hub
        #Fetch site (checking if origin_hub is correct or if initiative is public)
        try:
            site = origin_hub.sites.get(initiative.site_id)
        except:
            raise Exception("Please provide origin_hub of the initiative object, if the initiative is not publicly shared")
        #Create new initiative if destination hub is premium
        if self._hub._hub_enabled:
            #new initiative
            new_initiative = self._hub.initiatives.add(title=title, site=site)
            return new_initiative
        else:
            #Create new site if destination hub is basic/enterprise
            new_site = self._hub.sites.clone(site, pages=True, title=title)
            return new_site

    def get(self, initiative_id):
        """ 
        Returns the initiative object for the specified initiative_id.
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
            return Initiative(self._hub, initiativeItem)
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
            initiativelist.append(Initiative(self._hub, item))
        return initiativelist
        