''' Python program to connect with the database and fetch the GTFS data from the database. '''

import sqlite3
from sqlite3 import Error
import os

class Database:
    def __init__(self):
        self._FILE_DB = "GTFS_DB/gtfs_milan.sqlite"   
        self._path = os.path.dirname(os.path.abspath(__file__)) + "/" + self._FILE_DB
        # check if the database exists
        if not os.path.isfile(self._path):
            raise Exception("Database not found")
        else:
            print("Database found")
            
        
    def create_connection(self):
        """ 
        create a database connection to the SQLite database specified by the db_file
        :param db_file: database file
        :return: Connection object or None
        """
        conn = None
        try:
            conn = sqlite3.connect(self._path)
        except Error as e:
            print(e)

        return conn

    def close_connection(self, conn):
        """
        Close the connection with the database
        :param conn: the Connection object
        :return:
        """
        conn.close()

    def select_all_coordinates_stops(self):
        """
        Query all rows in the stops table
        :param conn: the Connection object
        :return:
        """
        conn = self.create_connection()
        cur = conn.cursor()
        cur.execute("SELECT stop_lat, stop_lon FROM stops")

        rows = cur.fetchall()

        self.close_connection(conn)
        return rows
    
    def select_all_coordinates_shapes(self):
        """
        Query all rows in the shapes table
        :param conn: the Connection object
        :return:
        """
        conn = self.create_connection()
        cur = conn.cursor()
        cur.execute("SELECT shape_id, shape_pt_lat, shape_pt_lon FROM shapes")

        rows = cur.fetchall()

        self.close_connection(conn)
        return rows
    
database = Database()