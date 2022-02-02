import math

class localizer():
    def __init__(self, num_antennas):
        self.quadrant_freq=[0 for _ in range(num_antennas)]
        self.total_reads=0

    def update(self, antenna_read):
        print(self.quadrant_freq)
        self.quadrant_freq[antenna_read-1]+=1
        self.total_reads+=1
        
    def localize(self): 
        #define the mapping from quadrant to position using unit vectors:
        
        pos = {
               0:[math.sqrt(2)/2, math.sqrt(2)/2],
               1:[-math.sqrt(2)/2,math.sqrt(2)/2],
               2:[-math.sqrt(2)/2,-math.sqrt(2)/2],
               3:[math.sqrt(2)/2,-math.sqrt(2)/2]
               }
        
        #Get the frequency of each quadrant for this epc
        #REMOVED, we now update this stuff each round! Don't need to recalc here
        '''
        quad_freq = []
        total_reads = 0
        for i in readings:
            i_epc = i[ 'epc96' ]
            i_quad = i[ 'antennastate' ]
            if i_epc == epc:
                quad_freq[ i_quad ] += 1
                total_reads += 1
        '''
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
        reflected_quad = (strongest_quad+(2)) % (2)
        adjusted_total_reads = self.total_reads - self.quadrant_freq[ reflected_quad ]
        norm_quad_freq=self.quadrant_freq
        norm_quad_freq[reflected_quad]=0
        
        #normalize quadrant frequency
        for j in range(len(self.quadrant_freq)):
            norm_quad_freq[j]/=adjusted_total_reads
        
        #Calculate the weighted location
        x_est = 0
        y_est = 0

        for i in range(len(norm_quad_freq)):
            x_est += norm_quad_freq[i]*pos[i][0]
            y_est += norm_quad_freq[i]*pos[i][1]

        rv = [ x_est, y_est ]
        #return dict of locations per epc ????
        return rv

