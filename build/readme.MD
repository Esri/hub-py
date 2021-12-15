### Building the Conda Package Using Jenkins:

1. Update the meta.yml (build number and source location)
2. Run the following:
    CD %WORKSPACE%
	conda build --croot "%WORKSPACE%/build" -c esri -c conda-forge -c http://dev0017935/ build
3. This will create whatever OS and conda version you are using.  To convert each one for different versions of Python or Operating Systems, use conda convert:

	conda convert -f --platform all "%WORKSPACE%/build\win-64\arcgishub-3.0.0-py38_%BUILD_NUMBER%.tar.bz2" -o "%WORKSPACE%/build"
	conda convert -f --platform all "%WORKSPACE%/build\win-64\arcgishub-3.0.0-py37_%BUILD_NUMBER%.tar.bz2" -o "%WORKSPACE%/build"
	conda convert -f --platform all "%WORKSPACE%/build\win-64\arcgishub-3.0.0-py39_%BUILD_NUMBER%.tar.bz2" -o "%WORKSPACE%/build"
	
