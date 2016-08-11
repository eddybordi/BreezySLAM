'''
pltslamshow.py - Pyplot classes for displaying maps and robots in SLAM projects

Copyright (C) 2016 Simon D. Levy and Matt Lubas

This code is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as 
published by the Free Software Foundation, either version 3 of the 
License, or (at your option) any later version.

This code is distributed in the hope that it will be useful,     
but WITHOUT ANY WARRANTY without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU Lesser General Public License 
along with this code.  If not, see <http://www.gnu.org/licenses/>.
'''

# Robot display params
ROBOT_COLOR_BGR                 = (0, 0, 255)
ROBOT_HEIGHT                    = 16
ROBOT_WIDTH                     = 10

ROBOT_HEIGHT_MM                 = 500
ROBOT_WIDTH_MM                  = 300

# Scan point display params
SCANPOINT_RADIUS                = 1
SCANPOINT_COLOR_BGR             = (0, 255, 0)

# Display params for odometry-based velocity
SENSOR_V_MAX_MM                 = 1000
SENSOR_THETA_MAX_DEG            = 20
SENSOR_BAR_X                    = 150
SENSOR_BAR_Y_OFFSET             = 3
SENSOR_BAR_WIDTH                = 20
SENSOR_BAR_MAX_HEIGHT           = 200
SENSOR_TEXT_X                   = 20
SENSOR_V_Y                      = 30
SENSOR_THETA_Y                  = 80
SENSOR_LABEL_COLOR_BGR          = (255,0,0)
SENSOR_POSITIVE_COLOR_BGR       = (0,255,0)
SENSOR_NEGATIVE_COLOR_BGR       = (0,0,255)

# Trajectory display params
TRAJECTORY_COLOR_BGR            = (255, 0, 0)

import cv
import matplotlib.pyplot as plt

# Arbitrary font for OpenCV
FONT_FACE                       = cv.CV_FONT_HERSHEY_COMPLEX

from math import sin, cos, radians

def _rotate(x, y, r, theta_deg):
    theta = radians(theta_deg)
    dx = r * cos(theta)
    dy = r * sin(theta)
    return x+dx, y+dy

class SlamShow(object):

    def __init__(self, map_size_pixels, map_scale_mm_per_pixel, window_name):
    
        # Store constants for update
        self.map_size_pixels = map_size_pixels
        self.map_scale_mm_per_pixel = map_scale_mm_per_pixel
        self.window_name = window_name

        # Create a byte array to display the map with a color overlay
        self.bgrbytes = bytearray(map_size_pixels * map_size_pixels * 3)
        
        # Create an empty OpenCV image to be filled with map bytes
        self.image = cv.CreateImageHeader((map_size_pixels,map_size_pixels), cv.IPL_DEPTH_8U, 3)
    
        # Create an OpenCV window for displaying the map
        cv.NamedWindow(window_name)
        
        # Set up font for displaying velocities
        self.font = cv.InitFont(FONT_FACE, 1, 1)
    
        # Display initial empty image
        cv.SetData(self.image, self.bgrbytes, self.map_size_pixels*3)
        cv.ShowImage(self.window_name, self.image)

        # Make a nice big (10"x10") figure
        fig = plt.figure(figsize=(10,10))

        # Store Python ID of figure to detect window close
        self.figid = id(fig)

        fig.canvas.set_window_title('SLAM 2D')

        self.ax = fig.gca()
        self.ax.set_aspect("auto")
        self.ax.set_autoscale_on(True)

        map_size_mm = map_scale_mm_per_pixel * map_size_pixels

        self.ax.set_xlim([0, map_size_mm])
        self.ax.set_ylim([0, map_size_mm])

        self.ax.set_xlabel('X (mm)')
        self.ax.set_ylabel('Y (mm)')

        self.ax.grid(False)

        #Starting vehicle at Center, 1600mm, 1600mm
        self._add_vehicle(16000,16000,0)

    def displayMap(self, mapbytes):
        
        # Interleave the grayscale map bytes into the color bytes
        self.bgrbytes[0::3] = mapbytes
        self.bgrbytes[1::3] = mapbytes
        self.bgrbytes[2::3] = mapbytes
        
        

        # Put color bytes into image
        cv.SetData(self.image, self.bgrbytes, self.map_size_pixels*3)
        
 
    def displayRobot(self, (x_mm, y_mm, theta_deg), color=ROBOT_COLOR_BGR, scale=1, line_thickness=1):

        # Get a polyline (e.g. triangle) to represent the robot icon
        robot_points = self.robot_polyline(scale)
        
        # Rotate the polyline by the current angle... would use rotate instead of this
        robot_points = map(lambda pt: rotate(pt, theta_deg), robot_points)
        
        # Convert the robot position from meters to pixels
        x_pix, y_pix = self.mm2pix(x_mm), self.mm2pix(y_mm)

        # Move the polyline to the current robot position ... would use rotate instead of this?
        robot_points = map(lambda pt: (x_pix+pt[0], y_pix+pt[1]), robot_points)
       
        # Add an icon for the robot
        cv.PolyLine(self.image, [robot_points], True, color, line_thickness) 

    def displayScan(self, scan, offset_mm = (0,0), color=SCANPOINT_COLOR_BGR):
   
       for point in scan:
           cv.Circle(self.image, (self.mm2pix(point[0]+offset_mm[0]), self.mm2pix(point[1]+offset_mm[1])), \
                     SCANPOINT_RADIUS, color)
      
               
    def displayVelocities(self, dxy_mm, dtheta_deg):
        
        # Add velocity bars
        self.show_velocity(dxy_mm,      SENSOR_V_MAX_MM,      '   dXY', SENSOR_V_Y)
        self.show_velocity(dtheta_deg,  SENSOR_THETA_MAX_DEG, 'dTheta', SENSOR_THETA_Y)
                       
    def displayTrajectory(self, trajectory):
        
        for k in range(1, len(trajectory)):
            
            x1_mm, y1_mm = trajectory[k-1]
            x2_mm, y2_mm = trajectory[k]
            
            cv.Line(self.image, 
                (self.mm2pix(x1_mm), self.mm2pix(y1_mm)), \
                (self.mm2pix(x2_mm), self.mm2pix(y2_mm)), \
                TRAJECTORY_COLOR_BGR)
    

    def setPose(self, x_mm, y_mm, theta_deg):
        '''
        Sets vehicle pose:
        X:      left/right   (cm)
        Y:      forward/back (cm)
        theta:  rotation (degrees)
        '''

        #remove old arrow
        self.vehicle.remove()
        
        #create a new arrow
        self._add_vehicle(x_mm, y_mm, theta_deg)

    def _add_vehicle(self, x_mm, y_mm, theta_deg):

        # Use a very short arrow shaft to orient the head of the arrow
        dx, dy = _rotate(0, 0, .1, theta_deg)

        self.vehicle=self.ax.arrow(x_mm, y_mm, dx, dy, head_width=ROBOT_WIDTH_MM, head_length=ROBOT_HEIGHT_MM, fc='r', ec='r')


    def refresh(self):                   

        # If we have a new figure, something went wrong (closing figure failed)
        if self.figid != id(plt.gcf()):
            return False

        # Redraw current objects without blocking
        plt.draw()

        # Refresh display, setting flag on window close or keyboard interrupt
        try:
            plt.pause(.01)
        except:
            return False

        # Display image
        cv.ShowImage(self.window_name, self.image)

        # Force image display, returning False if user hit ESC, True otherwise
        key = cvdisplay()
        return False if key==27 else True

    def waitkey(self, action):
        
        print('Hit any key to %s ...' % action)
        
        key = -1
        
        while True:
            
            key = cvdisplay()
            if key > -1:
                break
        
        return key    
        
        
    # Puts text in the image to label the velocity display
    def show_velocity(self, value, valspan, label, y):
        cv.PutText(self.image, label+':', (SENSOR_TEXT_X, y), self.font, SENSOR_LABEL_COLOR_BGR) 
        bar_x1 = SENSOR_BAR_X + SENSOR_BAR_MAX_HEIGHT
        bar_y1 = y + SENSOR_BAR_Y_OFFSET
        bar_x2 = bar_x1 + int(value / valspan * SENSOR_BAR_MAX_HEIGHT)
        bar_y2 = y - SENSOR_BAR_WIDTH + SENSOR_BAR_Y_OFFSET
        bar_color = SENSOR_NEGATIVE_COLOR_BGR if value < 0 else SENSOR_POSITIVE_COLOR_BGR
        cv.Rectangle(self.image, (bar_x1, bar_y1), (bar_x2, bar_y2), bar_color, cv.CV_FILLED) 


    # Builds an array of points for a polyline representing the robot, pointing 
    # rightward and centered at (0,0).
    # Currently builds an isoceles triangle pointing rightward
    def robot_polyline(self, scale):
        
        xlft = -ROBOT_HEIGHT / 2 * scale
        xrgt =  ROBOT_HEIGHT / 2 * scale
        ybot =  ROBOT_WIDTH / 2  * scale
        ytop = -ROBOT_HEIGHT / 2 * scale
        return [(xlft,ybot), (xrgt,0), (xlft,ytop)]


    # Converts millimeters to pixels
    def mm2pix(self, mm):
        return int(mm / float(self.map_scale_mm_per_pixel))
                
# Helpers -------------------------------------------------------------        
        
# Forces OpenCV image display, returning id of key it or -1 if none            
def cvdisplay():
    return cv.WaitKey(1)
    
# Rotates a point by a specified number of degrees
def rotate(pt, deg):
    rad = radians(deg)
    c = cos(rad)
    s = sin(rad)
    x,y = pt  
    return int(x*c - y*s), int(x*s + y*c)
    
