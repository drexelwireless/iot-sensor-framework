class Fuser():
    def __init__(self):
        self.input_history = {}
        self.estimates = {}
    
    #Function update
    #Inputs: 
    #   **kwargs - key value pair of position name and position
    #       EX: update(xn=1.5, yn=-0.9)
    #Outputs:
    #   None
    #Description: Update the input_history dictionary to contain another position to fuse
    def update(self, **kwargs):
        #TODO: change to queues so that we don't store too many readings
        for key, value in kwargs.items():
            if not key in self.input_history.keys():
                self.input_history[key] = []    
            self.input_history[key].append(value)

    #Function fuse
    #Inputs:
    #   none
    #Outputs:
    #   rv: Location estimate in the form [x,y]
    #Description: Estimates the true location of the tag based on fused estimates of the location
    def fuse(self): 
        x_count = 0
        x_est = 0
        y_count = 0
        y_est = 0
        for key, data in self.input_history.items():
            if key[0]=='x':
                x_est += data[-1]
                x_count += 1
            if key[0]=='y':
                y_est += data[-1]
                y_count += 1
        
        if x_count > 0:
            x_est /= x_count
        if y_count > 0:
            y_est /= y_count

        rv = (x_est, y_est)
        #return estimated position [x,y]
        return rv

    def fuse_kalman(self):
        #TODO: Get variance/kalmann parameters
        
        #TODO: Implement fusion
        
        rv = (xk, yk)
        return rv
