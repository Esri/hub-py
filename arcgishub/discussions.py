from collections import OrderedDict
import requests
import json

"""""
TODO: change the environment variable its calling on to one of 3: Literal['hubdev.arcgis.com', 'hubqa.arcgis.com', 'hub.arcgis.com']
"""""


class Post(OrderedDict):
    """
    Represents a Post within a Hub Discussion. 
    The levels of privacy and permissions for posts are determined by the channels they belong in.
    """

    def __init__(self, hub, postProperties):
        """
        Constructor for a Post
        """
        self._hub = hub
        self._gis = self._hub.gis

        self.postProperties = postProperties

        # used throughout all requests
        self.header = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self._gis._con.token,
            'Referer': self._gis._con._referer
        }

    def __repr__(self):
        return '<title:"%s" creator:%s created:%s>' % (self.title, self.creator, self.created)

    @property
    def id(self):
        """
        Returns the post's id
        """
        return self.postProperties['id']

    @property
    def title(self):
        """
        Returns the title of the post (if any)
        """
        return self.postProperties['title']

    @property
    def body(self):
        """
        Returns the body of the post
        """
        return self.postProperties['body']

    @property
    def discussion(self):
        """
        Returns the discussion URI that the post is related to
        """
        return self.postProperties['discussion']

    @property
    def creator(self):
        """
        Returns the author of the post
        """
        return self.postProperties['creator']

    @property
    def editor(self):
        """
        Returns the editor of the post
        """
        return self.postProperties['editor']

    @property
    def created(self):
        """
        Returns the created date and time of the post
        """
        return self.postProperties['createdAt']

    @property
    def updated(self):
        """
        Returns the time and date when the post was most recently updated
        """
        return self.postProperties['updatedAt']

    @property
    def status(self):
        """
        Returns the status of the post
        """
        return self.postProperties['status']

    @property
    def geometry(self):
        """
        Returns a property of GeoJSON if post is tied to a geography
        """
        return self.postProperties['geometry']
    
    @property
    def featureGeometry(self):
        """
        Returns a property of GeoJSON if post is tied to a featured geography
        """
        return self.postProperties['featureGeometry']
    
    @property
    def postType(self):
        """
        Returns a string of the type of post.
        """
        return self.postProperties['postType']

    @property
    def appInfo(self):
        """
        Returns additional information about the post in specific app context
        """
        return self.postProperties['appInfo']

    @property
    def channelId(self):
        """
        Returns the channel where this post is been created in
        """
        return self.postProperties['channelId']

    @property 
    def parentId(self):
        """
        Returns a parent post ID if this post is a reply
        """
        return self.postProperties['parentId']

    def update(self, body=None, title=None, discussion=None, geometry=None, featureGeometry=None, appInfo=None):
        """
        Update a post by providing the fields that need to be updated.

        ================    ===============================================================
        **Argument**        **Description**
        ----------------    ---------------------------------------------------------------
        body                Optional string. Primary text content of the post
        ----------------    ---------------------------------------------------------------
        title               Optional string. Title of the post (usually used when creating
                            the initial post of a discussion)
        ----------------    ---------------------------------------------------------------
        discussion          Optional string. This should be a valid Discussion URI that is 
                            used to show a post's relation to platform content such as items, 
                            datasets, and groups. Example: hub://item/uuid
        ----------------    ---------------------------------------------------------------
        geometry            Optional string. Geometry property of GeoJSON spec. Note that 
                            the spec requires geometries projected in WGS84.
        ----------------    ---------------------------------------------------------------
        featureGeometry     Optional string. Geometry property of GeoJSON spec. Note that 
                            the spec requires geometries projected in WGS84.
        ----------------    ---------------------------------------------------------------
        appInfo             Optional string. Generic field for application specific notes. 
                            For instance, this is used by Urban to encode a "topic" to posts.
        ================    ===============================================================


        Usage Example (Returns Post Object): 
        post = myHub.discussions.posts.get('itemid12345')
        post.update(title='this is my new title')
        >> <title:"this is my new title" creator:prod-pre-hub created:2021-08-25T20:37:20.440Z>
        """
        payload = {}

        if body:
            payload['body'] = body
        
        if title:
            payload['title'] = title
        
        if discussion:
            payload['discussion'] = discussion

        if geometry:
            payload['geometry'] = geometry
            
        if featureGeometry:
            payload['featureGeometry'] = featureGeometry

        if appInfo:
            payload['appInfo'] = appInfo
        
        url = f"https://{self._hub._hub_environment}/api/discussions/v1/posts/{self.id}"
        res = requests.patch(url, data=json.dumps(payload), headers=self.header)
        return Post(self._hub, res.json())

    def delete(self):
        """
        Deletes a post. Only the author or admin can delete a post.
         
        Returns True if post was successfully deleted
        Returns False if post was not able to be deleted
            - May not be deleted is user is not post author AND user lacks permission to modify posts in channel

        Usage Example:
        post = myHub.discussions.posts.get('itemid12345')
        post.delete()
        >> True
        """
        url = f"https://{self._hub._hub_environment}/api/discussions/v1/posts/{self.id}"
        res = requests.delete(url, headers=self.header)
        
        if res.json()['success']:
            return True
        return False

    def add_reaction(self, value):
        """
        Add a reaction to the post.

        ================    ===============================================================
        **Argument**        **Description**
        ----------------    ---------------------------------------------------------------
        value               Required string. Provide a reaction type such as "thumbs_up",
                            "heart", etc.   
        ================    ===============================================================

        Returns True if reaction was successfully added
        Returns False if reaction was not able to be added
            - Could result in 404: Post does not exist OR User lacks permission to read from post channel
            - Could result in 403: Reactions are disabled in post channel OR Specific reaction value is not allowed by post channel

        Usage Example:
        post = myHub.discussions.posts.get('itemid12345')
        post.add_reaction("thumbs_up")
        >> True
        """
        
        payload = {
            'postId': self.id,
            'value': value
        }

        url = f"https://{self._hub._hub_environment}/api/discussions/v1/reactions"
        res = requests.post(url, headers=self.header, data=json.dumps(payload))

        if res.json()['id']:
            # if there is a statusCode, then it was unable to add the reaction
            return Reaction(self._hub, res.json())
        else:
            return False

    def delete_reaction(self, id):
        """
        Delete a reaction on the post.

        ================    ===============================================================
        **Argument**        **Description**
        ----------------    ---------------------------------------------------------------
        value               Required string. The ID of the reaction to be deleted.
        ================    ===============================================================

        Returns True if reaction was sucessfully deleted
        Return False if something went wrong creating a reaction
            - Reaction was not found
            - User is not the reaction author

        Usage Example: 
        post = myHub.discussions.posts.get('itemid12345')
        post.delete_reaction("reactionid12345")
        >> True
        """
        
        url = f"https://{self._hub._hub_environment}/api/discussions/v1/reactions/{id}"
        res = requests.delete(url, headers=self.header)

        if res.json()['success']:
            return True
        return False

class PostManager(object):
    """
    Helper class for managing posts within a discussion. 
    """
    def __init__(self, hub, post=None):
        if post:
            self.post = post

        self._hub = hub
        self._gis = self._hub.gis

        # used throughout all requests
        self.header = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self._gis._con.token,
            'Referer': self._gis._con._referer
        }

    def search(self, max_posts=None):
        """
        Gets all the posts and returns in a paginated format.

        ================    ===============================================================
        **Argument**        **Description**
        ----------------    ---------------------------------------------------------------
        max_posts           Optional int. Number of posts to show since results are paginated.
                            Default value is -1 which will return all posts.
        ================    ===============================================================


        Usage Example:
        posts = myHub.discussions.posts.search(max_posts=3)
        >> [
                <title:"Title1" creator:prod-pre-hub created:2021-07-22T15:12:10.970Z>, 
                <title:"Hey" creator:prod-pre-hub created:2021-07-29T14:22:11.291Z>, 
                <title:"Discussion" creator:prod-pre-hub created:2021-08-16T17:50:33.956Z>
            ]
        """
        if max_posts:
            parameters = {
                'num': max_posts
            }
            res = requests.get(f"https://{self._hub._hub_environment}/api/discussions/v1/posts", headers=self.header, params=parameters)
        else:
           res = requests.get(f"https://{self._hub._hub_environment}/api/discussions/v1/posts", headers=self.header) 

        parsed_posts = res.json()['items']
    
        posts = []
        for post_properties in parsed_posts:
            posts.append(Post(self._hub, post_properties))
        
        return posts

    def get(self, id):
        """
        Gets a specific post by specifying the post's id.
        
        ================    ===============================================================
        **Argument**        **Description**
        ----------------    ---------------------------------------------------------------
        id                  Required string. The ID of the post to retrieve.
        ================    ===============================================================

        Usage Example:
        post = myHub.discussions.posts.get('itemid12345')
        >> <title:"My Title" creator:prod-pre-hub created:2021-09-04T04:00:18.957Z>
        """
        res = requests.get(f"https://{self._hub._hub_environment}/api/discussions/v1/posts/{id}", headers=self.header)
        postProperties = res.json()
        return Post(self._hub, postProperties)

    def add(self, postProperties):
        """
        Create a new post and add it to a discussion/channel.

        ================    ===============================================================
        **Argument**        **Description**
        ----------------    ---------------------------------------------------------------
        body                Required string. Primary text content of the post
        ----------------    ---------------------------------------------------------------
        title               Optional string. Title of the post (usually used when creating
                            the initial post of a discussion)
        ----------------    ---------------------------------------------------------------
        discussion          Optional string. This should be a valid Discussion URI that is 
                            used to show a post's relation to platform content such as items, 
                            datasets, and groups. Example: hub://item/uuid
        ----------------    ---------------------------------------------------------------
        geometry            Optional string. Geometry property of GeoJSON spec. Note that 
                            the spec requires geometries projected in WGS84.
        ----------------    ---------------------------------------------------------------
        featureGeometry     Optional string. Geometry property of GeoJSON spec. Note that 
                            the spec requires geometries projected in WGS84.
        ----------------    ---------------------------------------------------------------
        appInfo             Optional string. Generic field for application specific notes. 
                            For instance, this is used by Urban to encode a "topic" to posts.
        ----------------    ---------------------------------------------------------------
        postType            Optional string. Type of post. Current options are "text", 
                            "announcement", "poll", "question"
        ----------------    ---------------------------------------------------------------
        channelId           Required when not using access and groups. Specifies a channel 
                            that the post belongs to. Will be required with V2.
        ----------------    ---------------------------------------------------------------
        access              Required when not using channelId. This is the platform access 
                            level for the post. (Example: public, private, etc.)
        ----------------    ---------------------------------------------------------------
        groups              Required when not using channelId. This will be an array of 
                            platform group IDs used to designate private channels.
        ================    ===============================================================

        Usage Example:
        properties = {
            "access": "private",
            "groups": ["groupId12345"],
            "discussion": "hub://item/uuid",
            "title": "this is my title",
            "body": "hello there"
        }

        post = myHub.discussions.posts.add(properties)
        >> <title:"this is my title" creator:prod-pre-hub created:2021-08-25T20:37:20.440Z>
        """
        if postProperties['body'] == None:
            raise Exception("Must provide a body for the post!")

        payload = {
            'body': postProperties['body'],
        }

        # populate payload based on if channelId or access/groups were provided
        if ('channelId' in postProperties):
            payload['channelId'] = postProperties['channelId'] 
        else:
            payload['access'] = postProperties['access']
            payload['groups'] = postProperties['groups']

        non_optional = ['body', 'channelId', 'access', 'groups']
        for key, value in postProperties.items():
            if key not in non_optional:
                payload[key] = value

        res = requests.post(f"https://{self._hub._hub_environment}/api/discussions/v1/posts", data=json.dumps(payload), headers=self.header)    
        
        # for testing purposes
        print(res.body)

        # return post object is found, if not raise Exception
        try:
            return self.get(res.json()['id'])
        except:
            raise Exception('Post was not able to be created.')
        

class Channel(OrderedDict):
    """
    Represents a Channel within a Hub Discussion. 
    These channels are used to house posts and provide permissions/access to groups/orgs.
    """
    def __init__(self, hub, channelProperties):
        self.channelProperties = channelProperties

        self._hub = hub
        self._gis = self._hub.gis

        # used throughout all requests
        self.header = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self._gis._con._token,
            'Referer': self._gis._con._referer
        }

    def __repr__(self):
        return '<channel_id:%s access:"%s" groups:%s orgs:"%s" creator:%s>' % (self.id, self.access, self.groups, self.orgs, self.creator)


    @property
    def allowReply(self):
        """
        Returns a boolean representating if replies are allowed on posts.
        """
        return self.channelProperties['allowReply']

    @property
    def allowAnonymous(self):
        """
        Returns a boolean representing if anonymous users can create posts.
        """
        return self.channelProperties['allowAnonymous']

    @property
    def softDelete(self):
        """
        Returns a boolean showing if soft-delete strategy is on for posts, 
        meaning that DELETE actions flag posts as deleted as opposed to permanent deletion.
        """
        return self.channelProperties['softDelete']

    @property
    def defaultPostStatus(self):
        """
        Returns the status of a post when they are added to a channel 
        """
        return self.channelProperties['defaultPostStatus']

    @property
    def allowReaction(self):
        """
        Returns a boolean that shows if reactions are allowed on posts
        """
        return self.channelProperties['allowReaction']

    @property
    def id(self):
        """
        Returns the channel's id
        """
        return self.channelProperties['id']

    @property
    def access(self):
        """
        Returns a string that represents the platform level access for the channel
        """
        return self.channelProperties['access']

    @property
    def orgs(self):
        """
        Returns an array of org Ids used to define "org" and "public" channels
        """
        return self.channelProperties['orgs']

    @property
    def groups(self):
        """
         Returns an array of group Ids used to define "private" channels
        """
        return self.channelProperties['groups']
    
    @property
    def channelAclDefinition(self):
        """
        Returns the channel's channelAclDefinition
        """
        return self.channelProperties['channelAclDefinition']
    
    @property
    def blockWords(self):
        """
        Returns an array of phrases and words not allowed in this channel.
        """
        return self.channelProperties['blockWords']
    
    @property
    def name(self):
        """
        Returns a string of the name of the channel.
        """
        return self.channelProperties['name']
    
    @property
    def metadata(self):
        """
        Returns an object of the channel's metadata.
        """
        return self.channelProperties['metadata']

    @property
    def creator(self):
        """
        Returns the creator of the channel 
        """
        return self.channelProperties['creator']

    @property
    def editor(self):
        """
        Returns the editor of the channel
        """
        return self.channelProperties['editor']

    @property
    def created(self):
        """
        Returns the time and date of when the channel was created
        """
        return self.channelProperties['createdAt']

    @property
    def updated(self):
        """
        Returns the time and date of when the channel was updated
        """
        return self.channelProperties['updatedAt']

    def update(self, allowReply=None, allowAnonymous=None, softDelete=None, defaultPostStatus=None, allowReaction=None, allowedReactions=None, blockWords=None, name=None, metadata=None):
        """
        Update a channel by providing the fields that need to be updated. 
        Note: once a channel is created, its access, orgs, and groups configurations cannot be changed
        TO-DO: check on this note, implemented differently in hub.js and hub-discussions

        ================    ===============================================================
        **Argument**        **Description**
        ----------------    ---------------------------------------------------------------
        allowReply          Optional boolean. Determines whether replies can be made to posts.
        ----------------    ---------------------------------------------------------------
        allowAnonymous      Optional boolean. For public channels, determines whether 
                            unauthenticated users can create posts.
        ----------------    ---------------------------------------------------------------
        softDelete          Optional boolean. determines deletion policy for channel. 
                            When true, DELETE post operations will flag a post as deleted as 
                            opposed to SQL delete. soft deleted posts can be restored.
        ----------------    ---------------------------------------------------------------
        defaultPostStatus   Optional PostStatus ("pending", "approved", "rejected", "deleted", 
                            "hidden".). Initial status applied to posts in channel.
        ----------------    ---------------------------------------------------------------
        allowReaction       Optional boolean. Determines whether reactions can be created 
                            for posts in channel.
        ----------------    ---------------------------------------------------------------
        allowedReactions    Optional PostReaction ("thumbs_up", "thumbs_down", "thinking", 
                            "heart", "one_hundred", "sad", "laughing", "surprised"). 
                            Determines which reactions can be made for posts in channel. 
                            If null, all reactions can be made.
        ----------------    ---------------------------------------------------------------
        blockWords          Optional string array.
        ----------------    ---------------------------------------------------------------
        name                 Optional string.
        ----------------    ---------------------------------------------------------------
        metadata            Optional object.
        ================    ===============================================================        

        Usage Example:
        channel = myHub.discussions.channels.get('itemid12345')
        channel.update(allowReply=False)
        >> <channel_id:"itemid12345" access:"public" groups:[] creator:"prod-pre-hub">
        """
        payload = {}

        if allowReply:
            payload['allowReply'] = allowReply
        
        if allowAnonymous:
            payload['allowAnonymous'] = allowAnonymous

        if softDelete:
            payload['softDelete'] = softDelete

        if defaultPostStatus:
            payload['defaultPostStatus'] = defaultPostStatus

        if allowReaction:
            payload['allowReaction'] = allowReaction

        if allowedReactions:
            payload['allowedReactions'] = allowedReactions
        
        if blockWords:
            payload['blockWords'] = blockWords
        
        if name:
            payload['name'] = name
            
        if metadata:
            payload['metadata'] = metadata

        
        url = f"https://{self._hub._hub_environment}/api/discussions/v1/channels/{self.id}"
        res = requests.patch(url, data=json.dumps(payload), headers=self.header)
        return Channel(self._hub, res.json())

    def delete(self):
        """
        Deletes a channel. Only the manager of the channel can delete it.
        All posts owned by that channel will also be deleted.
        
        Usage Example:
        channel = myHub.discussions.channels.get('itemid12345')
        channel.delete()
        >> True
        """
        url = f"https://{self._hub._hub_environment}/api/discussions/v1/channels/{self.id}"
        res = requests.delete(url, headers=self.header)
        
        if res.json()['success']:
            return True
        return False

class ChannelManager(object):
    """
    Helper class for managing channels within a discussion. 
    """
    def __init__(self, hub, channel=None):
        if channel:
            self.channel = channel

        self._hub = hub
        self._gis = self._hub.gis

        # used throughout all requests
        self.header = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self._gis._con.token,
            'Referer': self._gis._con._referer
        }

    def search(self, max_channels=None):
        """
        Gets all the channels and returns in a paginated format.

        ================    ===============================================================
        **Argument**        **Description**
        ----------------    ---------------------------------------------------------------
        max_channels        Optional int. Number of channels to show since results are paginated.
        ================    ===============================================================


        Usage Example:
        channels = myHub.discussions.channels.search(max_posts=2)
        >>  [
                <channel_id:c1f592e6c6a84a37b94613df3683f5e5 access:"public" groups:[] creator:prod-pre-hub>, 
                <channel_id:e133ad215b2a4799883fad6b9f06b5c9 access:"public" groups:[] creator:prod-pre-hub>
            ]
        """

        if max_channels:
            parameters = {
                'num': max_channels
            }
            res = requests.get(f"https://{self._hub._hub_environment}/api/discussions/v1/channels", headers=self.header, params=parameters)
        else: 
            res = requests.get(f"https://{self._hub._hub_environment}/api/discussions/v1/channels", headers=self.header)
        
        parsed_channels = res.json()['items']
    
        channels = []
        for channel_properties in parsed_channels:
            channels.append(Channel(self._hub, channel_properties))

        return channels

    def get(self, id):
        """
        Gets a specific channel by specifying the channel's id.
        
        ================    ===============================================================
        **Argument**        **Description**
        ----------------    ---------------------------------------------------------------
        id                  Required string. The ID of the channel to retrieve.
        ================    ===============================================================

        Usage Example:
        channel = myHub.discussions.channels.get('itemid12345')
        >> <channel_id:"itemid12345" access:"public" groups:[] creator:"prod-pre-hub">
        """

        res = requests.get(f"https://{self._hub._hub_environment}/api/discussions/v1/channels/{id}", headers=self.header)
        channelProperties = res.json()
        return Channel(self._hub, channelProperties)

    def add(self, channelProperties):
        """
        ================    ===============================================================
        **Argument**        **Description**
        ----------------    ---------------------------------------------------------------
        access              Required string. Platform level access, can be any of the following:
                            org, private, public
        ----------------    ---------------------------------------------------------------
        groups              Required string array. Array of platform groupIds used to designate 
                            "private" channels
        ----------------    ---------------------------------------------------------------
        allowReply          Optional boolean, default: true. determines whether replies can 
                            be made to posts.
        ----------------    ---------------------------------------------------------------
        allowAnonymous      Optional boolean, default: false. For public channels, determines 
                            whether unauthenticated users can create posts.
        ----------------    ---------------------------------------------------------------
        softDelete          Optional boolean, default: true. determines deletion policy for 
                            channel. when true, DELETE post operations will flag a post as 
                            deleted as opposed to SQL delete. soft deleted posts can be restored.
        ----------------    ---------------------------------------------------------------
        defaultPostStatus   Optional string, default: "approved". Initial status applied to 
                            posts in channel. Possible inputs include: pending, approved, 
                            rejected, deleted, and hidden.
        ----------------    ---------------------------------------------------------------
        allowReaction       Optional boolean, default: true. determines whether reactions 
                            can be created for posts in channel.
        ----------------    ---------------------------------------------------------------
        allowedReactions    Optional string array, default null. determines which reactions
                            can be made for posts in channel. if null, all reactions can be 
                            made. Possible options for array include: "thumbs_up", 
                            "thumbs_down", "thinking", "heart", "one_hundred", "sad", 
                            "laughing", "surprised".
        ----------------    ---------------------------------------------------------------
        blockWords          Optional string array.  is used for words or phrases that can be 
                            used to automatically moderate posts.   
        ----------------    ---------------------------------------------------------------
        name                Optional string. 
        ----------------    ---------------------------------------------------------------
        metadata            Optional object.
        ----------------    ---------------------------------------------------------------
        channelAclDefinition    Optional object for V1.          
        ================    ===============================================================

        EXAMPLE RESPONSE:
        properties = {
            "access": "private",
            "groups": ["3ef"]
        }
        channel = myHub.discussions.channels.add(properties)
        >> <channel_id:"c1f592e6c6a84a37b94613df3683f5e5" access:"private" groups:["3ef"] creator:"prod-pre-hub">
        """
        if channelProperties['access'] == None or channelProperties['groups'] == None:
            print('must have both access and groups')
            return 

        payload = {
            'access': channelProperties['access'],
            'groups': channelProperties['groups']
        }

        non_optional = ['access', 'groups']
        for key, value in channelProperties.items():
            if key not in non_optional:
                payload[key] = value

        res = requests.post(f"https://{self._hub._hub_environment}/api/discussions/v1/channels", data=json.dumps(payload), headers=self.header)
        

        # return Channel object is found, if not raise Exception
        try:
            return self.get(res.json()['id'])
        except:
            raise Exception('Channel was not able to be created.')
    
class Reaction(OrderedDict):
    """
    Represents a Reaction within a Hub Discussion. 
    Reactions can only belong to a post and a post can have a variety of different reactions.
    """

    def __init__(self, hub, reactionProperties):
        """
        Constructor for a Reaction
        """
        self._hub = hub
        self._gis = self._hub.gis
        self.reactionProperties = reactionProperties

        self.header = {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + self._gis._con.token,
            'Referer': self._gis._con._referer
        }

    def __repr__(self):
        return '<value:"%s" creator:%s created:%s>' % (self.value, self.creator, self.created)
    
    @property
    def id(self):
        '''
        Returns the reaction's id.
        '''
        return self.reactionProperties['id']

    @property
    def postId(self):
        '''
        Returns the reaction's postId.
        '''
        return self.reactionProperties['postId']

    @property
    def value(self):
        '''
        Returns the reaction's value.
        '''
        return self.reactionProperties['value']

    @property
    def creator(self):
        '''
        Returns the reaction's creator.
        '''
        return self.reactionProperties['creator']

    @property
    def created(self):
        '''
        Returns the reaction's createdAt.
        '''
        return self.reactionProperties['createdAt']

    def delete(self, id):
        """
        Deletes a reaction.
        
        Usage Example:
        post = myHub.discussions.posts.get('itemid12345')
        reaction = post.add_reaction("thumbs_up")
        reaction.delete()
        >> True
        """

        res = requests.delete(f"https://{self._hub._hub_environment}/api/discussions/v1/reactions/{id}", headers=self.header)        
        if res.json()['success']:
            return True
        return False