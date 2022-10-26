from arcgis.gis import GIS
from arcgis._impl.common._mixins import PropertyMap
from arcgis._impl.common._isd import InsensitiveDict
from datetime import datetime
from collections import OrderedDict
import json
import os

class Page(OrderedDict):
    """
    Represents a page belonging to a site in Hub. A Page is a layout of 
    content that can be rendered within the context of a Site
    """
    
    def __init__(self, gis, pageItem):
        """
        Constructs an empty Page object
        """
        self.item = pageItem
        self._gis = gis
        try:
            self._pagedict = self.item.get_data()
            pmap = PropertyMap(self._pagedict)
            self.definition = pmap
        except:
            self.definition = None
            
    def __repr__(self):
        return '<%s title:"%s" owner:%s>' % (
            type(self).__name__, 
            self.item.title, 
            self.item.owner
        )
    
    @property
    def itemid(self):
        """
        Returns the item id of the page item
        """
        return self.item.id
    
    @property
    def title(self):
        """
        Returns the title of the page item
        """
        return self.item.title
    
    @property
    def description(self):
        """
        Getter/Setter for the page description
        """
        return self.item.description
    
    @description.setter
    def description(self, value):
        self.item.description = value

    @property
    def layout(self):
        """
        Return layout of a page
        """
        return InsensitiveDict(self.definition['values']['layout'])
        
    @property
    def owner(self):
        """
        Returns the owner of the page item
        """
        return self.item.owner

    @property
    def tags(self):
        """
        Returns the tags of the page item
        """
        return self.item.tags

    @tags.setter
    def tags(self, value):
        self.item.tags = value
    
    @property
    def slug(self):
        """
        Returns the page slug
        """
        return self.title.replace(' ', '-').lower()

    def update(self, page_properties=None, slug=None):
        """ Updates the page.
        
        .. note::
            
            For page_properties, pass in arguments for only the properties you want to be updated.
            All other properties will be untouched.  For example, if you want to update only the
            page's description, then only provide the description argument in page_properties.
        
        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        page_properties           Required dictionary. See URL below for the keys and values.
        ---------------------     --------------------------------------------------------------------
        slug                      Optional string. The slug or subdomain for the page.
        =====================     ====================================================================
        
        To find the list of applicable options for argument page_properties - 
        https://esri.github.io/arcgis-python-api/apidoc/html/arcgis.gis.toc.html#arcgis.gis.Item.update
        
        :return:
           A boolean indicating success (True) or failure (False).
        
        .. code-block:: python
            
            USAGE EXAMPLE: Update a page successfully
            
            page1 = mySite.pages.get('itemId12345')
            page1.update(page_properties={'description':'Description for page.'})
            
            >> True
        """
        _page_data = self.definition
        if page_properties:
            for key, value in page_properties.items():
                _page_data[key] = value
        if slug:
            #Fetch all the sites this page is connected to
            linked_sites = self.definition['values']['sites']
            for item in linked_sites:
                #Update the title and slug on the parent sites
                site_item = self._gis.content.get(item['id'])
                site = Site(self._gis, site_item)
                site.definition['values']['pages'] = [p for p in site.definition['values']['pages'] if p['id']!=self.itemid]
                _renamed_page = {}
                _renamed_page['id'] = self.itemid
                _renamed_page['title'] = slug
                _renamed_page['slug'] = slug
                site.definition['values']['pages'].append(_renamed_page)
                site.item.update(item_properties={'text': site.definition})
            #Update the slug on the page
            _page_data['title'] = slug
        return self.item.update(_page_data)

    def update_layout(self, layout):
        """ Updates the layout of the page.
        =====================     ====================================================================
        **Argument**              **Description**
        ---------------------     --------------------------------------------------------------------
        layout                    Required dictionary. The new layout dictionary to update to the page.
        =====================     ====================================================================
        :return:
           A boolean indicating success (True) or failure (False).
        .. code-block:: python
            USAGE EXAMPLE: Update a site successfully
            page1 = myHub.pages.get('itemId12345')
            page_layout = page1.layout
            page_layout.sections[0].rows[0].cards.pop(0)
            page1.update_layout(layout = page_layout)
            >> True
        """
        #Calling the update layout method for site with this page object
        Site.update_layout(self, layout)
 
    def delete(self):
        """
        Deletes the page. If unable to delete, raises a RuntimeException.
        
        :return:
            A bool containing True (for success) or False (for failure). 
        
        .. code-block:: python
        
            USAGE EXAMPLE: Delete a page successfully
        
            page1 = myHub.pages.get('itemId12345')
            page1.delete()
        
            >> True
        """
        #Unlink sites
        linked_sites = self.definition['values']['sites']
        for item in linked_sites:
            site_item = self._gis.content.get(item['id'])
            site = Site(self._gis, site_item)
            site.definition['values']['pages'] = [p for p in site.definition['values']['pages'] if p['id']!=self.itemid]
            site.item.update(item_properties={'text': site.definition})
        #Remove delete protection on page
        self.item.protect(enable=False)
        #Delete page item
        self.item.delete()

class PageManager(object):
    """
    Helper class for managing pages within a Hub. This class is not created by users directly. 
    An instance of this class, called 'pages', is available as a property of the Site object. Users
    call methods on this 'pages' object to manipulate (add, get, search, etc) pages for a site.
    """
    
    def __init__(self, gis, site=None):
        #self._hub = hub
        #self._gis = self._hub.gis
        self._gis = gis
        self._site = site

    def add(self, title, site=None):
        """ 
        Returns the pages linked to the specific site.
        
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        title                      Required string. The title of the new page.
        -----------------------    -------------------------------------------------------------
        site                       Optional string. The site object to add the page to.
        =======================    =============================================================
        
        :return:
           The page if successfully added, None if unsuccessful.
        
        .. code-block:: python
        
            USAGE EXAMPLE: Add a page to a site successfully 
        
            page1 = mySite.pages.add(title='My first page')
            page1.item

        .. code-block:: python
        
            USAGE EXAMPLE: Add a page successfully 
        
            page2 = myHub.pages.add(title='My second page', site=mySite)
            page2.item
        """
        #If site object is not provided
        if site is None:
            if self._site is None:
                raise Exception('Site object needed for adding page')
        #If called from a specified site
        if self._site is not None:
            site = self._site
        #Fetch site collab group if exists
        try:
            collab_group = self._gis.groups.get(site.collab_group_id)
        except:
            collab_group = None
    
        #For pages in ArcGIS Online
        if self._gis._portal.is_arcgisonline:
            #Set item details
            item_type = "Hub Page"
            typekeywords = "Hub, hubPage, JavaScript, Map, Mapping Site, Online Map, OpenData, selfConfigured, Web Map"
            description = "DO NOT DELETE OR MODIFY THIS ITEM. This item is managed by the ArcGIS Hub application. To make changes to this site, please visit https://hub.arcgis.com/overview/edit"
            image_card_url = 'https://cloud.githubusercontent.com/assets/7389593/20107607/1d2c3844-a5a7-11e6-9ec0-9e389033ccd8.jpg'
        #For Enterprise Sites
        else:
            item_type = "Site Page"
            typekeywords = "Hub, hubPage, JavaScript, Map, Mapping Site, Online Map, OpenData, selfConfigured, Web Map"
            description = "DO NOT DELETE OR MODIFY THIS ITEM. This item is managed by the ArcGIS Enterprise Sites application. To make changes to this site, please visit" + self._gis.url +"/apps/sites/#/home/overview/edit/"
            image_card_url = self._gis.url +'/apps/sites/images/placeholders/page-editor-card-image-placeholder.jpg'
        #Create page item
        _item_dict = {
                    "title":title,
                    "type": item_type,
                    "typeKeywords": typekeywords,
                    "description": description,
                    "culture": self._gis.properties.user.culture
                    }
        item =  self._gis.content.add(_item_dict, owner=self._gis.users.me.username)
        
        #share page with content and core team groups
        if collab_group:
            item.share(groups=[collab_group])

        #protect page from accidental deletion
        item.protect(enable=True)

        #Fetching page data
        data_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '_store/pages-data.json'))
        with open(data_path) as f:
            _page_data = json.load(f)

        #Updating page data
        _page_data['values']['layout']['sections'][1]['rows'][0]['cards'][0]['component']['settings']['src'] = image_card_url
        _page_data['values']['updatedBy'] = self._gis.users.me.username
        _data = json.dumps(_page_data)
        item.update(item_properties={'text': _data})
        page = Page(self._gis, item)
        #Link page to site
        status = site.pages.link(page)
        if status:
            return page

    def clone(self, page, site=None):
        """
        Clone allows for the creation of a page that is derived from the current page.

        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        page                Required Page object of page to be cloned.
        ---------------     --------------------------------------------------------------------
        site                Optional Site object.
        ===============     ====================================================================
        
        :return:
           Page.
        """
        from datetime import timezone
        now = datetime.now(timezone.utc)
        #New title
        title = page.title + "-copy-%s" % int(now.timestamp() * 1000)
        #Checking if item of correct type has been passed 
        if 'hubPage' not in page.item.typeKeywords:
            raise Exception("Incorrect item type. Page item needed for cloning.")
        #If site object is not provided
        if site is None:
            if self._site is None:
                raise Exception('Site object needed for cloning page')
        #If called from a specified site
        if self._site is not None:
            site = self._site
        #Create new page within site
        _cloned_page = site.pages.add(title)
        #Copy the page layout
        _cloned_page.definition['values']['layout'] = page.definition['values']['layout']
        #_data = json.dumps(_cloned_page.definition)
        _cloned_page.item.update(item_properties={'text': _cloned_page.definition})
        return Page(self._gis, _cloned_page.item)
        
    def get(self, page_id):
        """ 
        Returns the page object for the specified page_id.
        
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        page_id                    Required string. The page itemid.
        =======================    =============================================================
        
        :return:
            The page object if the item is found, None if the item is not found.
        
        .. code-block:: python
        
            USAGE EXAMPLE: Fetch a page successfully
            page1 = myHub.pages.get('itemId12345')
            page1.item
        """
        pageItem = self._gis.content.get(page_id)
        if 'hubPage' in pageItem.typeKeywords:
            return Page(self._gis, pageItem)
        else:
            raise TypeError("Item is not a valid page or is inaccessible.")

    def link(self, page, site=None, slug=None):
        """ 
        Links the page to the specific site.
        
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        page                       Required string. The page object to link.
        -----------------------    -------------------------------------------------------------
        site                       Optional string. The site object to link page to.
        -----------------------    -------------------------------------------------------------
        slug                       Optional string. The slug reference of the page in this site.
        =======================    =============================================================
        
        :return:
            A bool containing True (for success) or False (for failure).
        
        .. code-block:: python
        
            USAGE EXAMPLE: Link a page successfully for specific site
            mySite.pages.link(page_id='itemId12345')
        
            >> True
            
        .. code-block:: python
        
            USAGE EXAMPLE: Link a page successfully for site object passed as param
            myHub.pages.link(page_id='itemId12345', site=mySite)
        
            >> True
        """
        _new_page = {}
        _new_site = {}
        #Checking if item of correct type has been passed 
        if 'hubPage' not in page.item.typeKeywords:
            raise Exception("Incorrect item type. Page item needed for cloning.")
        #If site object is not provided
        if site is None:
            if self._site is None:
                raise Exception('Site object needed for linking page')
        #If called from a specified site
        if self._site is not None:
            site = self._site
        #Create new page dictionary
        _site_data = site.definition    
        _new_page['id'] = page.itemid
        _new_page['title'] = page.title
        if slug is not None:
            _new_page['slug'] = slug.replace(' ', '-').lower()
        else:
            _new_page['slug'] = page.slug
        _site_data['values']['pages'].append(_new_page)
        #Create new site dictionary
        _page_data = page.definition    
        _new_site['id'] = site.itemid
        _new_site['title'] = site.title
        _page_data['values']['sites'].append(_new_site)
        #Update page and site data with new linking
        page.item.update(item_properties={'text': _page_data})
        return site.item.update(item_properties={'text': _site_data})

    def unlink(self, page, site=None):
        """ 
        Unlinks the page from the specific site.
        
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        page                       Required string. The page object to unlink.
        -----------------------    -------------------------------------------------------------
        site                       Optional string. The site object to unlink page from.
        =======================    =============================================================
        
        :return:
            A bool containing True (for success) or False (for failure).
        
        .. code-block:: python
        
            USAGE EXAMPLE: Unlink a page successfully from specific site
        
            mySite.pages.unlink(page_id='itemId12345')
        
            >> True
            
        .. code-block:: python
        
            USAGE EXAMPLE: Unlink a page successfully from site object passed as param
        
            myHub.pages.unlink(page_id='itemId12345', site=mySite)
        
            >> True
        """
        #If site object is not provided
        if site is None:
            if self._site is None:
                raise Exception('Site object needed for unlinking page')
        #Checking if item of correct type has been passed 
        if 'hubPage' not in page.item.typeKeywords:
            raise Exception("Incorrect item type. Page item needed for cloning.")
        #If called from a specified site
        if self._site is not None:
            site = self._site
        #Update site and pages with the unlinking
        _site_data = site.definition  
        _page_data = page.definition  
        _site_data['values']['pages'] = [p for p in _site_data['values']['pages'] if p['id']!=page.itemid]
        _page_data['values']['sites'] = [s for s in _page_data['values']['sites'] if s['id']!=site.itemid]
        #Delete page if it has no other site linkage
        if len(_page_data['values']['sites'])==0:
            page.delete()
        #Update page data to reflect unlinking
        else:
            page.item.update(item_properties={'text': _page_data})
        #Update site data to reflect unlinking
        return site.item.update(item_properties={'text': _site_data})

    def search(self, title=None, owner=None, created=None, modified=None, tags=None):
        """ 
        Searches for pages.
        
        ===============     ====================================================================
        **Argument**        **Description**
        ---------------     --------------------------------------------------------------------
        title               Optional string. Return pages with provided string in title.
        ---------------     --------------------------------------------------------------------
        owner               Optional string. Return pages owned by a username.
        ---------------     --------------------------------------------------------------------
        created             Optional string. Date the page was created.
                            Shown in milliseconds since UNIX epoch.
        ---------------     --------------------------------------------------------------------
        modified            Optional string. Date the page was last modified.
                            Shown in milliseconds since UNIX epoch
        ---------------     --------------------------------------------------------------------
        tags                Optional string. User-defined tags that describe the page.
        ===============     ====================================================================
        
        :return:
           A list of matching pages.
        """

        pagelist = []

        if self._site is not None:
            pages = self._site.definition['values']['pages']
            items = [self._gis.content.get(page['id']) for page in pages]
        #Build search query
        else:
            query = 'typekeywords:hubPage'
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
        
        #Return searched pages
        for item in items:
            pagelist.append(Page(self._gis, item))
        return pagelist