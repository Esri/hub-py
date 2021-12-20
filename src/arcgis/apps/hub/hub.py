from arcgis.gis import GIS
from arcgis.features import FeatureLayer
from arcgis.geocoding import geocode
from arcgis._impl.common._mixins import PropertyMap
from arcgis.apps.hub import discussions
from arcgis.apps.hub.discussions import ChannelManager, PostManager
from arcgis.apps.hub.sites import SiteManager, PageManager
from arcgis.features.enrich_data import enrich_layer
from datetime import datetime
from collections import OrderedDict
import pandas as pd
import time
import matplotlib.pyplot as plt
import seaborn as sns
import json

sns.set(color_codes=True)


def _lazy_property(fn):
    """Decorator that makes a property lazy-evaluated."""
    # http://stevenloria.com/lazy-evaluated-properties-in-python/
    attr_name = "_lazy_" + fn.__name__

    @property
    def _lazy_property(self):
        if not hasattr(self, attr_name):
            setattr(self, attr_name, fn(self))
        return getattr(self, attr_name)

    return _lazy_property


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

    def __init__(
        self,
        url=None,
        username=None,
        password=None,
        key_file=None,
        cert_file=None,
        verify_cert=True,
        set_active=True,
        client_id=None,
        profile=None,
    ):
        # self.gis = gis
        self._username = username
        self._password = password
        if url == None:
            self.url = "https://www.arcgis.com"
        else:
            self.url = url
        self.gis = GIS(
            self.url,
            self._username,
            self._password,
            key_file,
            cert_file,
            verify_cert,
            set_active,
            client_id,
            profile,
        )
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
                _e_org_id = (
                    self.gis.properties.portalProperties.hub.settings.enterpriseOrg.orgId
                )
                return _e_org_id
            except AttributeError:
                try:
                    if (
                        self.gis.properties.subscriptionInfo.companionOrganizations.type
                        == "Enterprise"
                    ):
                        return "Enterprise org id is not available"
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
                _c_org_id = (
                    self.gis.properties.portalProperties.hub.settings.communityOrg.orgId
                )
                return _c_org_id
            except AttributeError:
                try:
                    if (
                        self.gis.properties.subscriptionInfo.companionOrganizations.type
                        == "Community"
                    ):
                        return "Community org id is not available"
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
                    _url = self.gis.properties.publicSubscriptionInfo.companionOrganizations[
                        0
                    ][
                        "organizationUrl"
                    ]
                except:
                    _url = self.gis.properties.subscriptionInfo.companionOrganizations[
                        0
                    ]["organizationUrl"]
                return "https://" + _url
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
                    _url = self.gis.properties.publicSubscriptionInfo.companionOrganizations[
                        0
                    ][
                        "organizationUrl"
                    ]
                except:
                    _url = self.gis.properties.subscriptionInfo.companionOrganizations[
                        0
                    ]["organizationUrl"]
                return "https://" + _url
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
        # self._gis = gis
        # self._hub = gis.hub
        try:
            self._initiativedict = self.item.get_data()
            pmap = PropertyMap(self._initiativedict)
            self.definition = pmap
        except:
            self.definition = None

    def __repr__(self):
        return '<%s title:"%s" owner:%s>' % (
            type(self).__name__,
            self.title,
            self.owner,
        )

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
        return self.item.properties["url"]

    @property
    def site_id(self):
        """
        Returns the itemid of the initiative site
        """
        try:
            return self.item.properties["siteId"]
        except:
            return self._initiativedict["steps"][0]["itemIds"][0]

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
        return self.item.properties["contentGroupId"]

    @property
    def collab_group_id(self):
        """
        Returns the groupId for the collaboration group
        """
        return self.item.properties["collaborationGroupId"]

    @property
    def followers_group_id(self):
        """
        Returns the groupId for the followers group
        """
        return self.item.properties["followersGroupId"]

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
        _users_e = self._gis.users.search(
            query="hubInitiativeId|" + self.itemid, outside_org=True
        )
        if community_gis is not None:
            _users_c = community_gis.users.search(
                query="hubInitiativeId|" + self.itemid, outside_org=True
            )
            _email = True
        for _user in _users_e:
            _temp = {}
            _temp["name"] = _user.fullName
            _temp["username"] = _user.username
            if _email:
                try:
                    _temp["email"] = _user.email
                except AttributeError:
                    for _user_c in _users_c:
                        if _user_c.username == _user.username:
                            try:
                                _temp["email"] = _user_c.email
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
        # Fetch Initiative Collaboration group
        _collab_group = self._gis.groups.get(self.collab_group_id)
        # Fetch Content Group
        _content_group = self._gis.groups.get(self.content_group_id)
        # share items with groups
        return self._gis.content.share_items(
            items_list, groups=[_collab_group, _content_group]
        )

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
            # Fetch Initiative Collaboration group
            _collab_group = self._gis.groups.get(self.collab_group_id)
            # Fetch Content Group
            _content_group = self._gis.groups.get(self.content_group_id)
            # Fetch Followers Group
            _followers_group = self._gis.groups.get(self.followers_group_id)
            # Fetch initiative site
            try:
                _site = self._hub.sites.get(self.site_id)
                _site.protected = False
                _site.delete()
            except:
                pass
            # Disable delete protection on groups and site
            try:
                _collab_group.protected = False
                _content_group.protected = False
                _followers_group.protected = False
            except:
                pass
            # Delete groups, site and initiative
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
        if "admin" not in self._gis.users.me.role:
            return Exception(
                "You do not have the administrator privileges to perform this action."
            )
        # fetch the core team for this initiative
        core_team = self._gis.groups.get(self.collab_group_id)
        # fetch the contents shared with this team
        core_team_content = core_team.content()
        # check if target_owner is part of core team, else add them to core team
        members = core_team.get_members()
        if (
            target_owner not in members["admins"]
            or target_owner not in members["users"]
        ):
            core_team.add_users(target_owner)
        # remove items from core team
        self._gis.content.unshare_items(core_team_content, groups=[core_team])
        # reassign to target_owner
        for item in core_team_content:
            item.reassign_to(target_owner)
        # fetch the items again since they have been reassigned
        new_content_list = []
        for item in core_team_content:
            item_temp = self._gis.content.get(item.id)
            new_content_list.append(item_temp)
        # share item back to the content group
        self._gis.content.share_items(
            new_content_list, groups=[core_team], allow_members_to_edit=True
        )
        # fetch content and followers teams
        content_team = self._gis.groups.get(self.content_group_id)
        followers_team = self._gis.groups.get(self.followers_group_id)
        # reassign them to target_owner
        content_team.reassign_to(target_owner)
        followers_team.reassign_to(target_owner)
        core_team.reassign_to(target_owner)
        return self._gis.content.get(self.itemid)

    def share(
        self, everyone=False, org=False, groups=None, allow_members_to_edit=False
    ):
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
        result1 = site.item.share(
            everyone=everyone,
            org=org,
            groups=groups,
            allow_members_to_edit=allow_members_to_edit,
        )
        result2 = self.item.share(
            everyone=everyone,
            org=org,
            groups=groups,
            allow_members_to_edit=allow_members_to_edit,
        )
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

    def update(
        self, initiative_properties=None, data=None, thumbnail=None, metadata=None
    ):
        """Updates the initiative.
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
                if key == "title":
                    title = value
                    # Fetch Initiative Collaboration group
                    _collab_group = self._gis.groups.get(self.collab_group_id)
                    # Fetch Content Group
                    _content_group = self._gis.groups.get(self.content_group_id)
                    # Fetch Followers Group
                    _followers_group = self._gis.groups.get(self.followers_group_id)
                    # Update title for all groups
                    _collab_group.update(title=title + " Core Team")
                    _content_group.update(title=title + " Content")
                    _followers_group.update(title=title + " Followers")
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

        # Define initiative
        if description is None:
            description = "Create your own initiative by combining existing applications with a custom site."
        _snippet = "Create your own initiative by combining existing applications with a custom site. Use this initiative to form teams around a problem and invite your community to participate."
        _item_dict = {
            "type": "Hub Initiative",
            "snippet": _snippet,
            "typekeywords": "Hub, hubInitiative, OpenData",
            "title": title,
            "description": description,
            "licenseInfo": "CC-BY-SA",
            "culture": "{{culture}}",
            "properties": {},
        }

        # Defining content, collaboration and followers groups
        _content_group_title = title + " Content"
        _content_group_dict = {
            "title": _content_group_title,
            "tags": [
                "Hub Group",
                "Hub Content Group",
                "Hub Site Group",
                "Hub Initiative Group",
            ],
            "access": "public",
        }
        _collab_group_title = title + " Core Team"
        _collab_group_dict = {
            "title": _collab_group_title,
            "tags": [
                "Hub Group",
                "Hub Initiative Group",
                "Hub Site Group",
                "Hub Core Team Group",
                "Hub Team Group",
            ],
            "access": "org",
        }
        _followers_group_title = title + " Followers"
        _followers_group_dict = {
            "title": _followers_group_title,
            "tags": [
                "Hub Initiative Group",
                " Hub Initiative Followers Group",
                "Hub Initiative Group",
            ],
            "access": "public",
        }

        # Create groups
        content_group = self._gis.groups.create_from_dict(_content_group_dict)
        collab_group = self._gis.groups.create_from_dict(_collab_group_dict)
        followers_group = self._gis.groups.create_from_dict(_followers_group_dict)

        # Protect groups from accidental deletion
        content_group.protected = True
        collab_group.protected = True
        followers_group.protected = True

        # Adding it to _item_dict
        if (
            content_group is not None
            and collab_group is not None
            and followers_group is not None
        ):
            _item_dict["properties"]["collaborationGroupId"] = collab_group.id
            _item_dict["properties"]["contentGroupId"] = content_group.id
            _item_dict["properties"]["followersGroupId"] = followers_group.id

        # Create initiative and share it with collaboration group
        item = self._gis.content.add(_item_dict, owner=self._gis.users.me.username)
        item.share(groups=[collab_group])

        # Create initiative site and set initiative properties
        _initiative = Initiative(self._hub, item)
        if site is None:
            site = _initiative.sites.add(title=title)
        else:
            site = _initiative.sites.clone(site, pages=True, title=title)
        item.update(
            item_properties={
                "url": site.url,
                "culture": self._gis.properties.user.culture,
            }
        )
        _initiative.site_url = site.item.url
        item.properties["site_id"] = site.itemid

        # update initiative data
        _item_data = {
            "assets": [
                {
                    "id": "bannerImage",
                    "url": self._hub.enterprise_org_url
                    + "/sharing/rest/content/items/"
                    + item.id
                    + "/resources/detail-image.jpg",
                    "properties": {
                        "type": "resource",
                        "fileName": "detail-image.jpg",
                        "mimeType": "image/jepg",
                    },
                    "license": {"type": "none"},
                    "display": {"position": {"x": "center", "y": "center"}},
                },
                {
                    "id": "iconDark",
                    "url": self._hub.enterprise_org_url
                    + "/sharing/rest/content/items/"
                    + item.id
                    + "/resources/icon-dark.png",
                    "properties": {
                        "type": "resource",
                        "fileName": "icon-dark.png",
                        "mimeType": "image/png",
                    },
                    "license": {"type": "none"},
                },
                {
                    "id": "iconLight",
                    "url": self._hub.enterprise_org_url
                    + "/sharing/rest/content/items/"
                    + item.id
                    + "/resources/icon-light.png",
                    "properties": {
                        "type": "resource",
                        "fileName": "icon-light.png",
                        "mimeType": "image/png",
                    },
                    "license": {"type": "none"},
                },
            ],
            "steps": [
                {
                    "id": "informTools",
                    "title": "Inform the Public",
                    "description": "Share data about your initiative with the public so people can easily find, download and use your data in different formats.",
                    "templateIds": [],
                    "itemIds": [site.itemid],
                },
                {
                    "id": "listenTools",
                    "title": "Listen to the Public",
                    "description": "Create ways to gather citizen feedback to help inform your city officials.",
                    "templateIds": [],
                    "itemIds": [],
                },
                {
                    "id": "monitorTools",
                    "title": "Monitor Progress",
                    "description": "Establish performance measures that incorporate the publics perspective.",
                    "templateIds": [],
                    "itemIds": [],
                },
            ],
            "indicators": [],
            "values": {
                "collaborationGroupId": collab_group.id,
                "contentGroupId": content_group.id,
                "followersGroupId": followers_group.id,
                "bannerImage": {
                    "source": "bannerImage",
                    "display": {"position": {"x": "center", "y": "center"}},
                },
            },
        }
        _data = json.dumps(_item_data)
        item.update(item_properties={"text": _data})
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
        # Checking if item of correct type has been passed
        if "hubInitiative" not in initiative.item.typeKeywords:
            raise Exception("Incorrect item type. Initiative item needed for cloning.")
        # New title
        if title is None:
            title = initiative.title + "-copy-%s" % int(now.timestamp() * 1000)
        # If cloning within same org
        if origin_hub is None:
            origin_hub = self._hub
        # Fetch site (checking if origin_hub is correct or if initiative is public)
        try:
            site = origin_hub.sites.get(initiative.site_id)
        except:
            raise Exception(
                "Please provide origin_hub of the initiative object, if the initiative is not publicly shared"
            )
        # Create new initiative if destination hub is premium
        if self._hub._hub_enabled:
            # new initiative
            new_initiative = self._hub.initiatives.add(title=title, site=site)
            return new_initiative
        else:
            # Create new site if destination hub is basic/enterprise
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
        initiativeItem = self._gis.content.get(initiative_id)
        if "hubInitiative" in initiativeItem.typeKeywords:
            return Initiative(self._hub, initiativeItem)
        else:
            raise TypeError("Item is not a valid initiative or is inaccessible.")

    def search(
        self, scope=None, title=None, owner=None, created=None, modified=None, tags=None
    ):
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

        # Build search query
        query = "typekeywords:hubInitiative"
        if title != None:
            query += " AND title:" + title
        if owner != None:
            query += " AND owner:" + owner
        if created != None:
            query += " AND created:" + created
        if modified != None:
            query += " AND modified:" + modified
        if tags != None:
            query += " AND tags:" + tags

        # Apply org scope and search
        if scope is None or self._gis.url == "https://www.arcgis.com":
            items = self._gis.content.search(query=query, max_items=5000)
        elif scope.lower() == "official":
            query += " AND access:public"
            _gis = GIS(self._hub.enterprise_org_url)
            items = _gis.content.search(query=query, max_items=5000)
        elif scope.lower() == "community":
            query += " AND access:public"
            _gis = GIS(self._hub.community_org_url)
            items = _gis.content.search(query=query, max_items=5000)
        elif scope.lower() == "all":
            items = self._gis.content.search(
                query=query, outside_org=True, max_items=5000
            )
        else:
            raise Exception("Invalid value for scope")

        # Return searched initiatives
        for item in items:
            initiativelist.append(Initiative(self._hub, item))
        return initiativelist


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
        return '<%s id:"%s" optional:%s>' % (
            type(self).__name__,
            self.indicatorid,
            self.optional,
        )

    @property
    def indicatorid(self):
        """
        Returns the id of the indicator
        """
        return self._indicatordict["id"]

    @property
    def indicator_type(self):
        """
        Returns the type (Data/Parameter) of the indicator
        """
        return self._indicatordict["type"]

    @property
    def optional(self):
        """
        Status if the indicator is optional (True/False)
        """
        return self._indicatordict["optional"]

    @property
    def url(self):
        """
        Returns the data layer url (if configured) of the indicator
        """
        try:
            return self._indicatordict["source"]["url"]
        except:
            return "Url not available for this indicator"

    @property
    def name(self):
        """
        Returns the layer name (if configured) of the indicator
        """
        try:
            return self._indicatordict["source"]["name"]
        except:
            return "Name not available for this indicator"

    @property
    def itemid(self):
        """
        Returns the item id of the data layer (if configured) of the indicator
        """
        try:
            return self._indicatordict["source"]["itemId"]
        except:
            return "Item Id not available for this indicator"

    @property
    def indicator_item(self):
        """
        Returns the item of the data layer (if configured) of the indicator
        """
        try:
            return self._gis.content.get(self.itemid)
        except:
            return "Item not configured for this indicator"

    @_lazy_property
    def data_sdf(self):
        """
        Returns the data for the indicator as a Spatial DataFrame.
        """
        try:
            _indicator_flayer = self.indicator_item.layers[0]
            return pd.DataFrame.spatial.from_layer(_indicator_flayer)
        except:
            return "Data not configured for this indicator"

    @property
    def mappings(self):
        """
        Returns the attribute mapping from data layer (if configured) of the indicator
        """
        try:
            return self._indicatordict["source"]["mappings"]
        except:
            return "Attribute mapping not available for this indicator"

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
            _indicator_id = self._indicatordict["id"]
            self._initiativedata["indicators"] = list(
                filter(
                    lambda indicator: indicator.get("id") != _indicator_id,
                    self._initiativedata["indicators"],
                )
            )
            _new_initiativedata = json.dumps(self._initiativedata)
            return self._initiativeItem.update(
                item_properties={"text": _new_initiativedata}
            )

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
            return "Weekday"
        if num >= 4:
            return "Weekend"

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
        # Bar chart for 1st category
        counts1 = df[attribute].value_counts()
        # Generates bar graph
        ax = counts1.plot(
            kind="barh", figsize=(12, 12), legend=True, fontsize=12, alpha=0.5
        )
        # X axis text and display style of categories
        ax.set_xlabel("Count", fontsize=12)
        # Y axis text
        ax.set_ylabel(attribute, fontsize=14)
        # Title
        ax.set_title("Bar chart for attribute " + attribute, fontsize=20)
        # Annotations
        for i in ax.patches:
            # get_width pulls left or right; get_y pushes up or down
            ax.text(
                i.get_width() + 0.1,
                i.get_y() + 0.31,
                str(round((i.get_width()), 2)),
                fontsize=10,
                color="dimgrey",
            )
        # results.append(plt)
        plt.show()

    def _pie_chart(self, df, attribute):
        """
        Generates a pie chart for given attribute if number of categories < 7.
        """

        # Data to plot
        types = list(df[attribute].unique())
        types = [category for category in types if category]
        sizes = df[attribute].value_counts()
        # Plot
        plt.figure(figsize=(6, 6))
        plt.title("Pie chart for " + attribute)
        plt.pie(sizes, labels=types, autopct="%1.2f%%", shadow=True, startangle=100)
        plt.axis("equal")
        # results.append(plt)
        plt.show()

    def _histogram_chart(self, df, attribute):
        """
        Generates a histogram for numerical attributes and datetime attributes.
        """
        plt.figure(figsize=(8, 8))
        bins = None
        if attribute == "month":
            bins = range(1, 13)
        n, bins, patches = plt.hist(df[attribute], bins=bins, alpha=0.5)
        plt.title("Distribution for " + attribute, fontsize=16)
        plt.xlabel(attribute, fontsize=16)
        plt.ylabel("Frequency", fontsize=16)
        # results.append(plt)
        plt.show()

    def _line_chart(self, df, attribute):
        """
        Generates a line chart for datetime attribute.
        """
        hours = df[attribute].unique().tolist()
        hours.sort()
        frequency = df[attribute].value_counts(normalize=True, sort=False)
        plt.plot(hours, frequency, color="red")
        plt.xlim(0, 24)
        plt.xlabel(attribute)
        plt.ylabel("Average count")
        plt.title("Average frequency for every " + attribute)
        # results.append(plt)
        plt.show()

    def _scatter_chart_boundary(self):
        """
        Generates a scatter chart for variables used to enrich boundaries.
        """
        enrich_variables = ["TOTPOP_CY", "MEDHINC_CY"]
        enriched = enrich_layer(
            self.url,
            analysis_variables=enrich_variables,
            output_name="boundaryEnriched_" + self.itemid + str(int(time.time())),
        )
        # Convert enriched to table
        enriched_flayer = enriched.layers[0]
        enriched_df = pd.DataFrame.spatial.from_layer(enriched_flayer)
        # Scatter plot
        fig, ax = plt.subplots(figsize=(8, 8))
        scatter = plt.scatter(
            enriched_df["TOTPOP_CY"], enriched_df["MEDHINC_CY"], c="blue", alpha=0.6
        )
        # X axis text and display style of categories
        ax.set_xlabel("Population per boundary", fontsize=14)
        # Y axis text
        ax.set_ylabel("Median household income per boundary", fontsize=14)
        # Title
        ax.set_title("Population v/s Median Household Income", fontsize=20)
        # results.append(plt)
        plt.show()
        return enriched

    def explore(self, subclass, display=True):
        """Returns exploratory analyses (statistics, charts, map) for the indicator.
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
        if subclass.lower() not in ["measure", "place", "boundary"]:
            raise Exception("Indicator not of valid subclass")

        # Calculating total number of features
        indicator_df = self.data_sdf
        total = (
            "Total number of " + self.indicatorid + ": " + str(indicator_df.shape[0])
        )
        results.append(total)

        # Getting column names
        category_columnNames = [
            field["name"]
            for field in self.mappings
            if field["type"] == "esriFieldTypeString"
        ]
        date_columnNames = [
            field["name"]
            for field in self.mappings
            if field["type"] == "esriFieldTypeDate"
        ]
        value_columnNames = [
            field["name"]
            for field in self.mappings
            if field["type"] == "esriFieldTypeInteger"
        ]

        # Call necessary charting methods for numerical variables
        if value_columnNames:
            for value in value_columnNames:
                # Average of value field
                results.append(
                    "Average number of "
                    + value
                    + " is: "
                    + str(indicator_df[value].mean())
                )
                self._histogram_chart(indicator_df, value)

        # Call necessary charting methods for categorical variables
        if category_columnNames:
            for category in category_columnNames:
                if len(indicator_df[category].unique()) < 7:
                    self._pie_chart(indicator_df, category)
                elif len(indicator_df[category].unique()) < 50:
                    self._bar_chart(indicator_df, category)

        # Call necessary charting methods for datetime variables
        if date_columnNames:
            for datetime in date_columnNames:
                indicator_df["date"] = indicator_df[datetime].apply(self._format_date)
                indicator_df["hour"] = indicator_df["date"].apply(self._hour)
                # Line chart for hourly distribution
                self._line_chart(indicator_df, "hour")

                indicator_df["date"] = pd.to_datetime(indicator_df["date"]).dt.date
                indicator_df["day_of_week"] = indicator_df["date"].apply(
                    lambda x: x.weekday()
                )
                indicator_df["day"] = indicator_df["day_of_week"].apply(self._week_day)
                # Pie chart for weekday-weekend distribution
                self._pie_chart(indicator_df, "day")

                indicator_df["month"] = indicator_df["date"].apply(self._month)
                try:
                    indicator_df["month"] = indicator_df["month"].astype(int)
                except:
                    pass
                # Histogram for monthly distribution
                self._histogram_chart(indicator_df, "month")

        # Map for this indicator
        indicator_map = self._gis.map()
        indicator_map.basemap = "dark-gray"
        if subclass.lower() == "place":
            indicator_map.add_layer(
                self.indicator_item.layers[0],
                {"title": "Locations for " + self.indicatorid, "opacity": 0.7},
            )
        elif subclass.lower() == "measure":
            indicator_map.add_layer(
                self.indicator_item.layers[0],
                {
                    "title": "Desnity based on occurrence",
                    "renderer": "HeatmapRenderer",
                    "opacity": 0.7,
                },
            )
        elif subclass.lower() == "boundary":
            # Scatter plot of variables enriching boundary
            enriched = self._scatter_chart_boundary()
            # Map of the enriched layer
            indicator_map.add_layer(
                {
                    "type": "FeatureLayer",
                    "url": enriched.url,
                    "renderer": "ClassedColorRenderer",
                    "field_name": "TOTPOP_CY",
                    "opacity": 0.75,
                }
            )
        # results.append(indicator_map)
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
            _indicatorId = indicator_properties["id"]
        except:
            return "Indicator properties must include id of indicator"
        if indicator_properties is not None:
            self._initiativedata["indicators"] = [
                dict(indicator_properties)
                if indicator["id"] == _indicatorId
                else indicator
                for indicator in self._initiativedata["indicators"]
            ]
            _new_initiativedata = json.dumps(self._initiativedata)
            status = self._initiativeItem.update(
                item_properties={"text": _new_initiativedata}
            )
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
        self._indicators = self._initiativedata["indicators"]

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
        _id = indicator_properties["id"]
        _added = False

        # Fetch initiative template data
        _itemplateid = self._initiativedata["source"]
        _itemplate = self._gis.content.get(_itemplateid)
        _itemplatedata = _itemplate.get_data()

        # Fetch solution templates associated with initiative template
        for step in _itemplatedata["steps"]:
            for _stemplateid in step["templateIds"]:
                _stemplates.append(_stemplateid)

        # Fetch data for each solution template
        for _stemplateid in _stemplates:
            _stemplate = self._gis.content.get(_stemplateid)
            _stemplatedata = _stemplate.get_data()

            # Check if indicator exists in solution
            for indicator in _stemplatedata["indicators"]:

                # add indicator to initiative
                if indicator["id"] == _id:
                    if self.get(_id) is not None:
                        return "Indicator already exists"
                    else:
                        self._initiativedata["indicators"].append(indicator_properties)
                        _new_initiativedata = json.dumps(self._initiativedata)
                        self._initiativeItem.update(
                            item_properties={"text": _new_initiativedata}
                        )
                        _added = True
                        # Share indicator item with content (open data) group
                        try:
                            item = self._gis.content.get(
                                indicator_properties["source"]["itemId"]
                            )
                            initiative = self._hub.initiatives.get(
                                self._initiativeItem.id
                            )
                            content_group = self._gis.groups.get(
                                initiative.content_group_id
                            )
                            item.share(groups=[content_group])
                        except:
                            pass
                        return Indicator(
                            self._gis, self._initiativeItem, indicator_properties
                        )
        if not _added:
            return "Invalid indicator id for this initiative"

    def get(self, indicator_id):
        """Returns the indicator object for the specified indicator_id.
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        indicator_id               Required string. The indicator identifier.
        =======================    =============================================================
        :return:
            The indicator object if the indicator is found, None if the indicator is not found.
        """
        for indicator in self._indicators:
            if indicator["id"] == indicator_id:
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
        if url != None:
            _indicators = [
                indicator
                for indicator in _indicators
                if indicator["source"]["url"] == url
            ]
        if item_id != None:
            _indicators = [
                indicator
                for indicator in _indicators
                if indicator["source"]["itemId"] == item_id
            ]
        if name != None:
            _indicators = [
                indicator
                for indicator in _indicators
                if indicator["source"]["name"] == name
            ]
        for indicator in _indicators:
            indicatorlist.append(Indicator(self._gis, self._initiativeItem, indicator))
        return indicatorlist


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
        self._eventdict = eventObject["attributes"]
        try:
            self._eventdict["geometry"] = eventObject["geometry"]
        except KeyError:
            self._eventdict["geometry"] = {"x": 0.00, "y": 0.00}
        pmap = PropertyMap(self._eventdict)
        self.definition = pmap

    def __repr__(self):
        return '<%s title:"%s" venue:%s>' % (
            type(self).__name__,
            self.title,
            self.venue,
        )

    @property
    def event_id(self):
        """
        Returns the unique identifier of the event
        """
        return self._eventdict["OBJECTID"]

    @property
    def title(self):
        """
        Returns the title of the event
        """
        return self._eventdict["title"]

    @property
    def venue(self):
        """
        Returns the location of the event
        """
        return self._eventdict["venue"]

    @property
    def address(self):
        """
        Returns the street address for the venue of the event
        """
        return self._eventdict["address1"]

    @property
    def initiative_id(self):
        """
        Returns the initiative id of the initiative the event belongs to
        """
        return self._eventdict["initiativeId"]

    @property
    def site_id(self):
        """
        Returns the site id of the initiative site
        """
        return self._eventdict["siteId"]

    @property
    def organizers(self):
        """
        Returns the name and email of the event organizers
        """
        return self._eventdict["organizers"]

    @property
    def description(self):
        """
        Returns description of the event
        """
        return self._eventdict["description"]

    @property
    def start_date(self):
        """
        Returns start date of the event in milliseconds since UNIX epoch
        """
        return self._eventdict["startDate"]

    @property
    def end_date(self):
        """
        Returns end date of the event in milliseconds since UNIX epoch
        """
        return self._eventdict["endDate"]

    @property
    def creator(self):
        """
        Returns creator of the event
        """
        return self._eventdict["Creator"]

    @property
    def capacity(self):
        """
        Returns attendance capacity for attendees of the event
        """
        return self._eventdict["capacity"]

    @property
    def attendance(self):
        """
        Returns attendance count for a past event
        """
        return self._eventdict["attendance"]

    @property
    def access(self):
        """
        Returns access permissions of the event
        """
        return self._eventdict["status"]

    @property
    def group_id(self):
        """
        Returns groupId for the event
        """
        return self._eventdict["groupId"]

    @property
    def is_cancelled(self):
        """
        Check if event is Cancelled
        """
        return self._eventdict["isCancelled"]

    @property
    def geometry(self):
        """
        Returns co-ordinates of the event location
        """
        return self._eventdict["geometry"]

    def add_attachment(self, image_url):
        """
        Allows for adding an image to an event.
        Event should be of type jpeg, jpg or png.
        Max size is 10MB.
        :return:
            A bool containing True (for success) or False (for failure).
        .. code-block:: python
            USAGE EXAMPLE: Add image to existing event
            event1 = myhub.events.get(24)
            event1.add_attachment(image_url)
            >> True
        """
        url = (
            "https://hub.arcgis.com/api/v3/events/"
            + self._hub.enterprise_org_id
            + "/Hub Events/FeatureServer/0/"
            + str(self.event_id)
            + "/addAttachment"
        )
        params = {"attachment": image_url, "token": self._gis._con.token}
        attachment = self._gis._con.post(path=url, postdata=params)

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
        params = {"f": "json", "objectIds": self.event_id}
        delete_event = self._gis._con.post(
            path="https://hub.arcgis.com/api/v3/events/"
            + self._hub.enterprise_org_id
            + "/Hub Events/FeatureServer/0/deleteFeatures",
            postdata=params,
        )
        return delete_event["deleteResults"][0]["success"]

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

        # Build event feature
        event_properties["OBJECTID"] = self.event_id
        _feature["attributes"] = self._eventdict
        for key, value in event_properties.items():
            _feature["attributes"][key] = value
        _feature["geometry"] = self.geometry
        event_data = [_feature]

        # Update event
        url = (
            "https://hub.arcgis.com/api/v3/events/"
            + self._hub.enterprise_org_id
            + "/Hub Events/FeatureServer/0/updateFeatures"
        )
        params = {"f": "json", "features": event_data}
        update_event = self._gis._con.post(path=url, postdata=params)
        return update_event["updateResults"][0]["success"]


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
        url = (
            "https://hub.arcgis.com/api/v3/events/"
            + self._hub.enterprise_org_id
            + "/Hub Events/FeatureServer/0/query"
        )
        params = {"f": "json", "outFields": "*", "where": "1=1"}
        all_events = self._gis._con.get(url, params)
        _events_data = all_events["features"]
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
        # Fetch initiaitve site id
        _initiative = self._hub.initiatives.get(event_properties["initiativeId"])
        event_properties["siteId"] = _initiative.site_id
        # Set organizers if not provided
        try:
            event_properties["organizers"]
        except:
            _organizers_list = [
                {
                    "name": self._gis.users.me.fullName,
                    "contact": self._gis.users.me.email,
                    "username": self._gis.users.me.username,
                }
            ]
            _organizers = json.dumps(_organizers_list)
            event_properties["organizers"] = _organizers
        # Set sponsors if not provided
        try:
            event_properties["sponsors"]
            event_properties["sponsors"] = json.dumps(event_properties["sponsors"])
        except:
            _sponsors = []
            event_properties["sponsors"] = json.dumps(_sponsors)
        # Set onlineLocation if not provided
        try:
            event_properties["onlineLocation"]
        except:
            _onlineLocation = ""
            event_properties["onlineLocation"] = _onlineLocation
        # Set geometry if not provided
        try:
            event_properties["geometry"]
            geometry = event_properties["geometry"]
            del event_properties["geometry"]
        except:
            geometry = geocode(event_properties["address1"])[0]["location"]

        event_properties["schemaVersion"] = 2
        event_properties["location"] = ""
        event_properties["url"] = event_properties["title"].replace(" ", "-").lower()

        # Generate event id for new event
        event_id = max([event.event_id for event in self._all_events()]) + 1

        # Create event group
        _event_group_dict = {
            "title": event_properties["title"],
            "access": "public",
            "tags": ["Hub Event Group", "Open Data", "hubEvent|" + str(event_id)],
        }
        _event_group = self._gis.groups.create_from_dict(_event_group_dict)
        _event_group.protected = True
        event_properties["groupId"] = _event_group.id

        # Build new event feature and create it
        _feature["attributes"] = event_properties
        _feature["geometry"] = geometry
        event_data = [_feature]
        url = (
            "https://hub.arcgis.com/api/v3/events/"
            + self._hub.enterprise_org_id
            + "/Hub Events/FeatureServer/0/addFeatures"
        )
        params = {"f": "json", "features": event_data}
        add_event = self._gis._con.post(path=url, postdata=params)
        try:
            add_event["addResults"]
            return self.get(add_event["addResults"][0]["objectId"])
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
        if initiative_id != None:
            # events =
            events = [event for event in events if initiative_id == event.initiative_id]
        if title != None:
            events = [event for event in events if title in event.title]
        if venue != None:
            events = [event for event in events if venue in event.venue]
        if organizer_name != None:
            events = [event for event in events if organizer_name in event.organizers]
        return events

    def get(self, event_id):
        """Get the event for the specified event_id.
        =======================    =============================================================
        **Argument**               **Description**
        -----------------------    -------------------------------------------------------------
        event_id                   Required integer. The event identifier.
        =======================    =============================================================
        :return:
            The event object.
        """
        url = (
            "https://hub.arcgis.com/api/v3/events/"
            + self._hub.enterprise_org_id
            + "/Hub Events/FeatureServer/0/"
            + str(event_id)
        )
        params = {"f": "json"}
        feature = self._gis._con.get(url, params)
        return Event(self._gis, feature["feature"])

    def get_map(self):
        """
        Plot all events for a Hub in an embedded webmap within the notebook.
        """
        _events_layer = self._gis.content.search(
            query="typekeywords:hubEventsLayer", max_items=5000
        )[0]
        event_map = self._gis.map(zoomlevel=2)
        event_map.basemap = "dark-gray"
        event_map.add_layer(
            _events_layer, {"title": "Event locations for this Hub", "opacity": 0.7}
        )
        return event_map
