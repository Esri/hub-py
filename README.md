# arcgishub
* The `arcgishub` package acts as the Python interface to ArcGIS Hub. It aims to serve both, the core team and community user-base of Hub by allowing automation of several Hub worksflows and simplifying the use of the Hub information model. 
* The library now equips users with tools needed to work with the __Sites__ in your Hub or Enterprise organization. You can create new sites and pages, search for existing sites and pages, as well as edit their layout and clone them, not only within the same organization, but over to different organizations as well.
* It is built over the `arcgis` Python API. Ensure you are using the most updated version of the `arcgis` API to use `arcgishub`.  Click [here](https://developers.arcgis.com/python/) to learn more about the `arcgis` API.
* The intended UI for this API is the Jupyter Notebook development environment. 
* This API is built to work with Sites in Enterprise versions >= 10.8

In order to install Python, install the bundle that comes with the Anaconda distribution (Refer [this](https://www.anaconda.com/distribution/))

### Steps to install

Execute the following command in the terminal

``` pip install -e git+https://github.com/esri/hub-py.git#egg=arcgishub ```

Once installed, test it by launching an instance of Jupyter Notebook and importing the package

``` from arcgishub import hub ```


### Steps to upgrade package

Execute the following command in the terminal

``` pip install -e git+https://github.com/esridc/hub-py.git#egg=arcgishub ```

Once installed, test it by launching an instance of Jupyter Notebook and importing the package

``` from arcgishub import hub ```

Test if the version has been upgraded by following with the command

``` 
import arcgishub
arcgishub.__version__ 
```

### Getting Started

The first step to interacting with `arcgishub` is creating an instance of a Hub and exploring all that it contains.
For example:

```  
from arcgishub import hub
myHub = hub.Hub("https://cityx.maps.arcgis.com", username, password) # or the url of your ArcGIS Online organization
initiatives = myHub.initiatives.search()
print(initiatives)
```

fetches a list containing all the initiatives within this Hub. Click [here](https://github.com/esridc/hub-py/wiki) for more information and API reference about the functionality supported.

### User Guides

Example notebooks for using this API to work with your Hub are provided in the [examples](https://github.com/esridc/hub-py/tree/master/examples) directory.

If you are working with `arcgishub` >=v2.1.0, you will find the above examples and functionality supported in this API under the [For arcgishub](https://github.com/esridc/hub-py/tree/master/examples/For%20arcgishub) folder.

Older versions of this API can also be found in the [ArcGIS API for Python](https://developers.arcgis.com/python/). You can find user guides to access Hub using it, under the [For ArcGIS API for Python](https://github.com/esridc/hub-py/tree/master/examples/For%20ArcGIS%20API%20for%20Python) subdirectory.


We encourage you to provide feedback/issues in implementation, under GitHub [issues](https://github.com/esridc/hub-py/issues) for this repo.
