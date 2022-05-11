from collections import OrderedDict
from arcgishub.utils import _lazy_property

class Indicator(OrderedDict):
    """
    Represents an indicator within an initiative. Initiatives use Indicators to standardize 
    data sources for ready-to-use analysis and comparison. Indicators are measurements of a system 
    including features, calculated metrics, or quantified goals. 
    """
    
    def __init__(self, gis, initiativeItem, indicatorObject):
        """
        Constructs an empty Indicator object
        """
        self._gis = gis
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
            return self._indicatordict['source']['name']
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
    def indicator_item(self):
        """
        Returns the item of the data layer (if configured) of the indicator
        """
        try:
            return self._gis.content.get(self.itemid)
        except:
            return 'Item not configured for this indicator'

    @_lazy_property
    def data_sdf(self):
        """
        Returns the data for the indicator as a Spatial DataFrame.
        """
        try:
            _indicator_flayer = self.indicator_item.layers[0]
            return pd.DataFrame.spatial.from_layer(_indicator_flayer)
        except:
            return 'Data not configured for this indicator'
        
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

    def _format_date(self, date):
        """
        Return date in Y-M-D
        """
        epoch_time = str(date)
        return epoch_time

    def _week_day(self, num):
        """
        Return Weekday/Weekend
        """
        if num < 4:
            return 'Weekday'
        if num >= 4:
            return 'Weekend'

    def _month(self, date):
        """
        Return month number
        """
        return str(date)[5:7]

    def _hour(self, date):
        """
        Return hour number
        """
        return str(date)[11:13]

    def _bar_chart(self, df, attribute):
        """
        Generates a bar chart for given attribute if number of categories >= 7.
        """
        #Bar chart for 1st category
        counts1 = df[attribute].value_counts()
        #Generates bar graph
        ax = counts1.plot(kind='barh', figsize=(12, 12), legend=True, fontsize=12, alpha=0.5)
        #X axis text and display style of categories
        ax.set_xlabel("Count", fontsize=12)
        #Y axis text
        ax.set_ylabel(attribute, fontsize=14)
        #Title
        ax.set_title("Bar chart for attribute "+attribute, fontsize=20)
        #Annotations
        for i in ax.patches:
            # get_width pulls left or right; get_y pushes up or down
            ax.text(i.get_width()+.1, i.get_y()+.31, str(round((i.get_width()), 2)), fontsize=10, color='dimgrey')
        #results.append(plt)
        plt.show()

    def _pie_chart(self, df, attribute):
        """
        Generates a pie chart for given attribute if number of categories < 7.
        """
        
        #Data to plot
        types = list(df[attribute].unique())
        types = [category for category in types if category]
        sizes = df[attribute].value_counts()
        #Plot
        plt.figure(figsize=(6,6))
        plt.title('Pie chart for '+attribute)
        plt.pie(sizes, labels=types,
            autopct='%1.2f%%', shadow=True, startangle=100)
        plt.axis('equal')
        #results.append(plt)
        plt.show()

    def _histogram_chart(self, df, attribute):
        """
        Generates a histogram for numerical attributes and datetime attributes.
        """
        plt.figure(figsize=(8,8))
        bins=None
        if attribute=='month':
            bins=range(1,13)
        n, bins, patches = plt.hist(df[attribute], bins=bins, alpha=0.5)
        plt.title("Distribution for "+attribute, fontsize=16)
        plt.xlabel(attribute, fontsize=16)
        plt.ylabel("Frequency", fontsize=16)
        #results.append(plt)
        plt.show()

    def _line_chart(self, df, attribute):
        """
        Generates a line chart for datetime attribute.
        """
        hours = df[attribute].unique().tolist()
        hours.sort()
        frequency = df[attribute].value_counts(normalize=True, sort=False)
        plt.plot(hours, frequency, color='red')
        plt.xlim(0, 24)
        plt.xlabel(attribute)
        plt.ylabel('Average count')
        plt.title('Average frequency for every '+attribute)
        #results.append(plt)
        plt.show()

    def _scatter_chart_boundary(self):
        """
        Generates a scatter chart for variables used to enrich boundaries.
        """
        enrich_variables = ['TOTPOP_CY', 'MEDHINC_CY']
        enriched = enrich_layer(self.url, analysis_variables=enrich_variables, output_name='boundaryEnriched_'+self.itemid+str(int(time.time())))
        #Convert enriched to table
        enriched_flayer = enriched.layers[0]
        enriched_df = pd.DataFrame.spatial.from_layer(enriched_flayer)
        #Scatter plot
        fig, ax =  plt.subplots(figsize=(8,8))
        scatter = plt.scatter(enriched_df['TOTPOP_CY'], enriched_df['MEDHINC_CY'], c='blue', alpha=0.6)
        #X axis text and display style of categories
        ax.set_xlabel("Population per boundary", fontsize=14)
        #Y axis text
        ax.set_ylabel("Median household income per boundary", fontsize=14)
        #Title
        ax.set_title("Population v/s Median Household Income", fontsize=20)
        #results.append(plt)
        plt.show()
        return enriched

    def explore(self, subclass, display=True):
        """ Returns exploratory analyses (statistics, charts, map) for the indicator.
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        subclass                   Required string. Defines the conceptual classification.
                                   Valid values are 'measure', 'place', 'boundary'.
        -----------------------    -------------------------------------------------------------
        display                    Optional boolean. Indicates if the infographics should be
                                   displayed inline or returned in a list. Default is True.
        =======================    =============================================================
        :return:
            List of generated analyses if `display=False` else displays results in the notebok.
        """
        results = []
        if subclass.lower() not in ['measure', 'place', 'boundary']:
            raise Exception("Indicator not of valid subclass")

        #Calculating total number of features
        indicator_df = self.data_sdf
        total = 'Total number of '+self.indicatorid+': '+str(indicator_df.shape[0])
        results.append(total)

        #Getting column names
        category_columnNames = [field['name'] for field in self.mappings if field['type']=='esriFieldTypeString']
        date_columnNames = [field['name'] for field in self.mappings if field['type']=='esriFieldTypeDate']
        value_columnNames = [field['name'] for field in self.mappings if field['type']=='esriFieldTypeInteger']
      
        #Call necessary charting methods for numerical variables
        if value_columnNames:
            for value in value_columnNames:
            #Average of value field
                results.append('Average number of '+value+ ' is: '+str(indicator_df[value].mean()))
                self._histogram_chart(indicator_df, value)

        #Call necessary charting methods for categorical variables
        if category_columnNames:
            for category in category_columnNames:
                if len(indicator_df[category].unique()) < 7:
                    self._pie_chart(indicator_df, category)
                elif len(indicator_df[category].unique()) < 50:
                    self._bar_chart(indicator_df, category)

        #Call necessary charting methods for datetime variables
        if date_columnNames:
            for datetime in date_columnNames:
                indicator_df['date'] = indicator_df[datetime].apply(self._format_date)
                indicator_df['hour'] = indicator_df['date'].apply(self._hour)
                #Line chart for hourly distribution
                self._line_chart(indicator_df, 'hour')

                indicator_df['date'] = pd.to_datetime(indicator_df['date']).dt.date
                indicator_df['day_of_week'] = indicator_df['date'].apply(lambda x: x.weekday()) 
                indicator_df['day'] = indicator_df['day_of_week'].apply(self._week_day)
                #Pie chart for weekday-weekend distribution
                self._pie_chart(indicator_df, 'day')

                indicator_df['month'] = indicator_df['date'].apply(self._month)
                try:
                    indicator_df['month'] = indicator_df['month'].astype(int)
                except:
                    pass
                #Histogram for monthly distribution
                self._histogram_chart(indicator_df, 'month')
    
        #Map for this indicator
        indicator_map = self._gis.map()
        indicator_map.basemap = 'dark-gray'
        if subclass.lower()=='place':
            indicator_map.add_layer(self.indicator_item.layers[0], {'title':'Locations for '+self.indicatorid,'opacity':0.7})
        elif subclass.lower()=='measure':
            indicator_map.add_layer(self.indicator_item.layers[0], {'title':'Desnity based on occurrence','renderer':'HeatmapRenderer','opacity':0.7})
        elif subclass.lower()=='boundary':
            #Scatter plot of variables enriching boundary
            enriched = self._scatter_chart_boundary()
            #Map of the enriched layer
            indicator_map.add_layer({"type":"FeatureLayer",
                "url": enriched.url,
                "renderer":"ClassedColorRenderer",
                "field_name":"TOTPOP_CY",
                "opacity":0.75
               })
        #results.append(indicator_map)
        return indicator_map

    
    def get_data(self):
        """
        Retrieves the data associated with an indicator
        """
        return self.definition
    
    def update(self, indicator_properties=None):
        """
        Updates properties of an indicator
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
        self._hub = self._gis.hub
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
                        #Share indicator item with content (open data) group
                        try:
                            item = self._gis.content.get(indicator_properties['source']['itemId'])
                            initiative = self._hub.initiatives.get(self._initiativeItem.id)
                            content_group = self._gis.groups.get(initiative.content_group_id)
                            item.share(groups=[content_group])
                        except:
                            pass
                        return Indicator(self._gis, self._initiativeItem, indicator_properties)
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
            return Indicator(self._gis, self._initiativeItem, _indicator)
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
            indicatorlist.append(Indicator(self._gis, self._initiativeItem, indicator))
        return indicatorlist
