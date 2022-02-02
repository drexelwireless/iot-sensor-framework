import math

class localizer():
    #Description:
    #   quadrant_freq - an array containing 1 element for each quardant (each antenna)
    #   total_reads - an int containing the total number of reads
    def __init__(self, num_antennas):
        self.quadrant_freq=[0 for _ in range(num_antennas)]
        self.total_reads=0
    
    #Function update
    #Inputs: 
    #   antenna_read - a new read from the antenna. Is simply the index of the quadrant it came from
    #Outputs:
    #   None
    #Description: Update the quadrant_freq array to include a new reading from the antenna
    def update(self, antenna_read):
        #TODO: Eventually remove elements from the quadrant_freq array once it has been long enough
        self.quadrant_freq[antenna_read-1]+=1
        self.total_reads+=1

    #Function localize
    #Inputs:
    #   none
    #Outputs:
    #   rv: Location estimate in the form [x,y]
    #Description: Estimates the location of the tag based on the current value of the quadrant_freq array
    def localize(self): 
        #define the mapping from quadrant to position using unit vectors:
        pos = {
               0:[math.sqrt(2)/2, math.sqrt(2)/2],
               1:[-math.sqrt(2)/2,math.sqrt(2)/2],
               2:[-math.sqrt(2)/2,-math.sqrt(2)/2],
               3:[math.sqrt(2)/2,-math.sqrt(2)/2]
               }
        
        #if low number of reads or there is only 1 antenna, do not do multipath
        if self.total_reads<5 or len(self.quadrant_freq)==1:
            rv=[-1,-1]
            return rv

        #find multipath quadrant
        #start by getting the quadrant with the most reads
        most_reads=max(self.quadrant_freq)
        for i in range(len(self.quadrant_freq)):
                if self.quadrant_freq[i]==most_reads:
                    strongest_quad=i
        
        #get the opposite quadrant to the strongest and remove reads                    
        reflected_quad = (strongest_quad+(2)) % (4)
        adjusted_total_reads = self.total_reads - self.quadrant_freq[ reflected_quad ]
        norm_quad_freq=self.quadrant_freq
        norm_quad_freq[reflected_quad]=0
        
        """
        #normalize quadrant frequency
        for j in range(len(self.quadrant_freq)):
            norm_quad_freq[j]/=adjusted_total_reads
        """
        #Calculate the weighted location
        x_est = 0
        y_est = 0
        for i in range(len(norm_quad_freq)):
            x_est += norm_quad_freq[i]*pos[i][0]
            y_est += norm_quad_freq[i]*pos[i][1]
        
        #normalize quadrant frequency into a unit vector
        magnitude = math.sqrt((x_est**2) + (y_est**2))
        rv = [ x_est / magnitude, y_est / magnitude] 
        
        #return estimated position [x,y]
        return rv

