from arcgis.gis import GIS
from arcgis.features import FeatureLayer
from arcgis.geocoding import geocode
from arcgis._impl.common._mixins import PropertyMap
from arcgishub import discussions
from arcgishub.discussions import ChannelManager, PostManager
from arcgishub.sites import SiteManager, PageManager
from arcgishub.events import EventManager, Event
from arcgishub.initiatives import InitiativeManager, Initiative
from arcgis.features.enrich_data import enrich_layer
from datetime import datetime
from collections import OrderedDict
from arcgishub.utils import _lazy_property

import pandas as pd
import time
import matplotlib.pyplot as plt
import seaborn as sns
import json
sns.set(color_codes=True)

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
    ----------------    ---------------------------------------------------------------
    key_file            Optional string. The file path to a user's key certificate for PKI
                        authentication
    ----------------    ---------------------------------------------------------------
    cert_file           Optional string. The file path to a user's certificate file for PKI
                        authentication. If a PFX or P12 certificate is used, a password is required.
                        If a PEM file is used, the key_file is required.
    ----------------    ---------------------------------------------------------------
    verify_cert         Optional boolean. If a site has an invalid SSL certificate or is
                        being accessed via the IP or hostname instead of the name on the
                        certificate, set this value to False.  This will ensure that all
                        SSL certificate issues are ignored.
                        The default is True.
                        **Warning** Setting the value to False can be a security risk.
    ----------------    ---------------------------------------------------------------
    set_active          Optional boolean. The default is True.  If True, the GIS object
                        will be used as the default GIS object throughout the whole
                        scripting session.
    ----------------    ---------------------------------------------------------------
    client_id           Optional string. Used for OAuth authentication.  This is the
                        client ID value.
    ----------------    ---------------------------------------------------------------
    profile             Optional string. the name of the profile that the user wishes to use
                        to authenticate, if set, the identified profile will be used to login
                        to the specified GIS.
    ================    ===============================================================
    """
    
    def __init__(self, url=None, username=None, password=None, key_file=None, cert_file=None,
                 verify_cert=True, set_active=True, client_id=None, profile=None):
        #self.gis = gis
        self._username = username
        self._password = password
        if url==None:
            self.url = 'https://www.arcgis.com'
        else:
            self.url = url
        self.gis = GIS(self.url, self._username, self._password, key_file, cert_file, verify_cert,
                        set_active, client_id, profile)
        try:
            self._gis_id = self.gis.properties.id
        except AttributeError:
            self._gis_id = None

    @property
    def _hub_enabled(self):
        """
        Returns True if Hub is enabled on this org
        """
        try:
            self.gis.properties.subscriptionInfo.hubSettings.enabled
            return True
        except:
            return False
            
    @property
    def enterprise_org_id(self):
        """
        Returns the AGOL org id of the Enterprise Organization associated with this Hub.
        """

        if self._hub_enabled:
            try:
                _e_org_id = self.gis.properties.portalProperties.hub.settings.enterpriseOrg.orgId
                return _e_org_id
            except AttributeError:
                try:
                    if self.gis.properties.subscriptionInfo.companionOrganizations.type=='Enterprise':
                        return 'Enterprise org id is not available'
                except:
                    return self._gis_id
        else:
            raise Exception("Hub does not exist or is inaccessible.")

    @property
    def community_org_id(self):
        """
        Returns the AGOL org id of the Community Organization associated with this Hub.
        """
        if self._hub_enabled:
            try:
                _c_org_id = self.gis.properties.portalProperties.hub.settings.communityOrg.orgId
                return _c_org_id
            except AttributeError:
                try:
                    if self.gis.properties.subscriptionInfo.companionOrganizations.type=='Community':
                        return 'Community org id is not available'
                except:
                    return self._gis_id
        else:
            raise Exception("Hub does not exist or is inaccessible.")
        
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
    
    @_lazy_property
    def sites(self):
        """
        The resource manager for Hub sites. See :class:`~hub.sites.SiteManager`.
        """
        return SiteManager(self)

    @_lazy_property
    def pages(self):
        """
        The resource manager for Hub pages. See :class:`~hub.sites.PageManager`.
        """
        return PageManager(self.gis)

    @_lazy_property
    def discussions(self):
        discussions.posts = PostManager(self)
        discussions.channels = ChannelManager(self)
        """
        The resource manager for Hub Discussions.
        """
        return discussions
