# arcgishub
* The `arcgishub` package acts as the Python interface to ArcGIS Hub. It aims to serve both, the enterprise and community user-base of Hub by allowing automation of several Hub worksflows and simplifying the use of the Hub information model. 
* It is built over the `arcgis` Python API. Click [here](https://developers.arcgis.com/python/) to learn more about the API.
* The intended UI for this API is the Jupyter Notebook development environment. 

In order to install Python, install the bundle that comes with the Anaconda distribution (Refer [this](https://www.anaconda.com/distribution/))

### Steps to install

Execute the following command in the terminal

``` pip install -e git+https://github.com/esridc/hub-py.git#egg=arcgishub ```

Once installed, test it by launching an instance of Jupyter Notebook and importing the package

``` from arcgishub import hub ```


### Steps to upgrade package

Execute the following command in the terminal

``` pip install -e git+https://github.com/esridc/hub-py.git#egg=arcgishub ```

Once installed, test it by launching an instance of Jupyter Notebook and importing the package

``` from arcgishub import hub ```

Test if the version has been upgraded by following with the command

``` arcgishub.__version__ ```

### Getting Started

The first step to interacting with `arcgishub` is creating an instance of a Hub and exploring all that it contains.
For instance:

```  
myHub = hub.Hub("https://cityxcommunity.maps.arcgis.com/home/index.html") #or the url of your org
myHub.initiatives.search()
```

fetches a list containing all the initiatives within this Hub. Click [here](https://github.com/esridc/hub-py/wiki) for more information and API reference about the functionality supported.

### User Guides

Example notebooks for using this API to work with your Hub are provided in the [examples](https://github.com/esridc/hub-py/tree/master/examples) directory.

If you are using the most recent version of the [ArcGIS API for Python](https://developers.arcgis.com/python/) you can find user guides to access Hub using it, under the [For ArcGIS API for Python](https://github.com/esridc/hub-py/tree/master/examples/For%20ArcGIS%20API%20for%20Python) subdirectory.

If you choose to work with `arcgishub` instead, you will find the above examples and functionality supported in this API. User guides for any new functionality supported by `arcgishub` can be found under the [For arcgishub](https://github.com/esridc/hub-py/tree/master/examples/For%20arcgishub) folder.


### Future versions will allow:

1. To search for initiatives/events/indicators/apps across Hubs, instead of within a particular Hub.
2. Searching for a Hub based on Name or Location.
3. Searching for Hubs based on Initiatives adopted.
4. Searching for initiatives based on Indicators used.

We encourage you to provide feedback/issues in implementation, under GitHub [issues](https://github.com/esridc/hub-py/issues) for this repo.
