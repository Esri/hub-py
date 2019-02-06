# arcgishub
The `arcgishub` package acts as the Python interface to ArcGIS Hub. It intends to serve both, the city and community user-base of Hub by allowing automation of several Hub worksflows and simplifying the use of the Hub information model.
This package is built to be used in the Jupyter Notebook development environment. 

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
myHub.initiatives()
```

fetches a list containing all the initiatives within this Hub. Click [here](https://github.com/esridc/hub-py/wiki/Implemented-methods-and-its-usage) for more information about the functionality supported.


### Future versions will allow:

1. To search for initiatives/events/indicators/apps across Hubs, instead of within a particular Hub.
2. Searching for a Hub based on Name or Location.
3. Searching for Hubs based on Initiatives adopted.
4. Searching for initiatives based on Indicators used.

We encourage you to provide feedback/issues in implementation, under GitHub [issues](https://github.com/esridc/hub-py/issues) for this repo.
