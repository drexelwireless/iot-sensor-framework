#!/bin/bash
# Test Project API Key is DC24220D883E8300E98346510F44645D
# Permanent API Key is A865941DDD1277361BD2EB3D417B443F
# REDCap API endpoint is https://redcap.drexelmed.edu/redcap/api/
python3 server.py -d -r -e 2 -b https://redcap.drexelmed.edu/redcap/api/ -t DC24220D883E8300E98346510F44645D
