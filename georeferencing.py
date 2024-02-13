
from pyproj import Transformer
import rasterio
import csv
import skimage
import numpy as np




class GCPList():

    def __init__(self, filename):

        self.filename = filename
        self.gcps = self.load_gcps(filename)


    def load_gcps(self, filename, src_crs='epsg:4326', dst_crs='epsg:4326'):

        # Some GCP files use 'epsg:3857' as src_crs

        gcps = []
        with open(filename, 'r') as csv_file:

            # Open CSV file
            reader = csv.reader(csv_file)

            # Skip first two rows (header)
            next(reader, None)
            next(reader, None)

            # Create transformer
            transformer = Transformer.from_crs(src_crs, dst_crs)

            # Iterate through rows
            for gcp in reader:

                # Transform lat/lon
                if src_crs.lower() != dst_crs.lower():
                    lon = gcp[0]
                    lat = gcp[1]
                    lon, lat = transformer.transform(lon, lat)
                else:
                    # TODO: figure out why these need to be swapped
                    lon = gcp[1]
                    lat = gcp[0]

                # Read GCP fields from row
                gcps.append(rasterio.control.GroundControlPoint(row=float(gcp[2]),
                                                                col=float(gcp[3]), 
                                                                x=float(lon), 
                                                                y=float(lat)))

            # Close file
            csv_file.close()

        # Return list of GCPs
        return gcps
            


class Georeferencer(GCPList):

    def __init__(self, filename, image_height, image_width):
        super().__init__(filename)

        self.image_height = image_height
        self.image_width = image_width

        # Estimate polynomial transform
        transform, lat_coefficents, lon_coefficients = self.estimate_polynomial_transform(self.gcps)

        # Generate latitude and longitude arrays
        latitudes, longitudes = self.generate_polynomial_lat_lon_arrays(transform, self.image_height, self.image_width)

        self.latitudes = latitudes
        self.longitudes = longitudes


    def estimate_polynomial_transform(self, gcps):

        # https://scikit-image.org/docs/stable/api/skimage.transform.html#polynomialtransform

        img_coords = np.zeros((len(gcps),2))
        geo_coords = np.zeros((len(gcps),2))

        # Load image coords and geospatial coords from GCPs.
        for i,gcp in enumerate(gcps):
            img_coords[i,0] = gcp.row + 0.5
            img_coords[i,1] = -gcp.col*3 - 0.5# works for erie_2023-05-17_1553Z
            #img_coords[i,1] = gcp.col*3 + 684 # works for erie_2022_08_27T16_05_36
            #img_coords[i,1] = -gcp.col*3
            geo_coords[i,0] = gcp.y
            geo_coords[i,1] = gcp.x
        
        # Estimate transform
        transform = skimage.transform.estimate_transform('polynomial', img_coords, geo_coords, 2)

        # Get coefficients from transform
        lat_coefficients = transform.params[0]
        lon_coefficients = transform.params[1]

        # Return the coefficients
        return transform, lat_coefficients, lon_coefficients 



    def generate_polynomial_lat_lon_arrays(self, transform: skimage.transform.PolynomialTransform, image_height: int, image_width: int):

            # Create empty arrays to write lat and lon data
            lats = np.empty((image_height, image_width))
            lons = np.empty((image_height, image_width))

            # Generate X and Y coordinates
            x_coords, y_coords = np.meshgrid(np.arange(image_height), np.arange(image_width), indexing='ij')

            # Combine the X and Y coordinates into a list of (x, y) tuples
            image_coordinates = list(zip(x_coords.ravel(), y_coords.ravel()))

            # Transform X and Y coordnates to geospatial coordinates
            geo_coordinates = transform(image_coordinates)

            # Copy transformed lat and lon coords into lat and lon arrays
            for idx,coord in enumerate(image_coordinates):
                lons[coord] = geo_coordinates[idx,0]
                lats[coord] = geo_coordinates[idx,1]

            return lats, lons




    def compute_polynomial_transform(self, X, Y, lat_coefficients, lon_coefficients):
        
        ## Example usage:
        #for Y in range(0, image_height):
        #    for X in range(0, image_width):
        #        lon, lat = self.compute_polynomial_transform(Y, X, lat_coefficients, lon_coefficients)
        #        lats[Y,X] = lat
        #        lons[Y,X] = lon


        #X = sum[j=0:order]( sum[i=0:j]( a_ji * x**(j - i) * y**i ))

        #x.T = [a00 a10 a11 a20 a21 a22 ... ann
        #   b00 b10 b11 b20 b21 b22 ... bnn c3]

        #X = (( a_00 * x**(0 - 0) * y**0 ))
        #(( a_10 * x**(1 - 0) * y**0 ))  +  (( a_11 * x**(1 - 1) * y**1 ))
        #(( a_20 * x**(2 - 0) * y**0 ))  +  (( a_21 * x**(2 - 1) * y**1 )) 
        #                                +  (( a_22 * x**(2 - 2) * y**2 ))

        c = lat_coefficients
        lat = c[0] + c[1]*X + c[2]*Y + c[3]*X**2 + c[4]*X*Y + c[5]*Y**2

        c = lon_coefficients
        lon = c[0] + c[1]*X + c[2]*Y + c[3]*X**2 + c[4]*X*Y + c[5]*Y**2

        return (lat, lon)


