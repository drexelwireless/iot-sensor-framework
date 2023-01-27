import numpy as np
class spherical_localizer():
    def __init__(self):
        self.coords = []

    def getLocation(self, rssi, phase, port):
        """
        Finds 2-dimensional coordinates from rssi and phase angle
        
        Inputs
        ------
        list: a 2-dimesnional array of polar coordinates (r,theta)
        
        Returns
        -------
        list: a 2-demsional array of cartesian coordinates (x,y)
        """
        # Analog of magnitude of vector in 2D space
        rssi += 256

        # Analog of direction of vector in 2D space

        antennastate = 0 # change if stacking antenna states
        
        xyCoor = [-1,-1]
        
        xyCoor[0] = abs( rssi ) * np.cos(
        phase + (np.pi / 2 * (port-1)) + (np.pi / 4 * antennastate) )  # X coordinate
        xyCoor[1] = abs( rssi ) * np.sin(
        phase + (np.pi / 2 * (port-1)) + (np.pi / 4 * antennastate) )  # Y coordinate
        
        self.coords.append(xyCoor)

        return xyCoor  # dict of locations per epc
