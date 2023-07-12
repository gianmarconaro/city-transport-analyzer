''' Python program to connect with the database and fetch the GTFS data from the database. '''

import sqlite3
from sqlite3 import Error
import os

class Database:
    def __init__(self):
        self._FILE_DB = "GTFS_DB/gtfs_milan_metro.db"   
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
        cur.execute("SELECT stop_id, stop_name, stop_lat, stop_lon, wheelchair_boarding FROM stops")

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
        cur.execute("SELECT shape_id, shape_pt_lat, shape_pt_lon, shape_pt_sequence FROM shapes")

        rows = cur.fetchall()

        self.close_connection(conn)
        return rows 
    
    # def select_timetables_given_stop_id(self, stop_id):
    #     """
    #     Query all rows in the stop_times table given a stop_id then join with trips based on trip_id
    #     :param conn: the Connection object
    #     :return:
    #     """
    #     conn = self.create_connection()
    #     cur = conn.cursor()
    #     cur.execute("SELECT trip_id, arrival_time, departure_time, stop_sequence FROM stop_times WHERE stop_id = ?", (stop_id,))

    #     rows = cur.fetchall()

    #     self.close_connection(conn)
    #     return rows
    
    # def select_trips_given_trip_id(self, trip_id):
    #     """
    #     Query all rows in the trips table given a trip_id
    #     :param conn: the Connection object
    #     :return:
    #     """
    #     conn = self.create_connection()
    #     cur = conn.cursor()
    #     cur.execute("SELECT route_id, service_id, trip_headsign FROM trips WHERE trip_id = ?", (trip_id,))

    #     rows = cur.fetchall()

    #     self.close_connection(conn)
    #     return rows
    
    # def select_routes_given_route_id(self, route_id):
    #     """
    #     Query all rows in the routes table given a route_id
    #     :param conn: the Connection object
    #     :return:
    #     """
    #     conn = self.create_connection()
    #     cur = conn.cursor()
    #     cur.execute("SELECT route_short_name, route_long_name, route_type FROM routes WHERE route_id = ?", (route_id,))

    #     rows = cur.fetchall()

    #     self.close_connection(conn)
    #     return rows

    def select_information_given_stop_id(self, stop_id):
        """
        Query all relevant information given a stop_id
        :param conn: the Connection object
        :return:
        """
        conn = self.create_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT st.trip_id, st.arrival_time, st.departure_time, st.stop_sequence,
                tr.route_id, tr.service_id, tr.trip_headsign,
                ro.route_short_name, ro.route_long_name, ro.route_type
            FROM stops AS s
            JOIN stop_times AS st ON s.stop_id = st.stop_id
            JOIN trips AS tr ON st.trip_id = tr.trip_id
            JOIN routes AS ro ON tr.route_id = ro.route_id
            WHERE s.stop_id = ?
            """, (stop_id,))

        rows = cur.fetchall()

        self.close_connection(conn)
        return rows
    
    def select_transport_by_shape_id(self, shape_id):
        """
        Query 
        :param conn: the Connection object
        :return:
        """
        conn = self.create_connection()
        cur = conn.cursor()
        cur.execute("""
            SELECT DISTINCT route_id
            FROM trips AS tr
            JOIN shapes AS sh ON tr.shape_id = sh.shape_id
            WHERE sh.shape_id = ?
            """, (shape_id,))

        rows = cur.fetchall()

        self.close_connection(conn)
        return rows






    def select_next_arrival_and_departure_time_for_each_transport(self, stop_id, short_name, current_time):
        """
        Query all rows in the stops table
        :param conn: the Connection object
        :return:
        """
        conn = self.create_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT st.arrival_time, st.departure_time, tr.trip_headsign, ro.route_short_name, ro.route_long_name, ro.route_type
            FROM stops AS s
            JOIN stop_times AS st ON s.stop_id = st.stop_id
            JOIN trips AS tr ON st.trip_id = tr.trip_id
            JOIN routes AS ro ON tr.route_id = ro.route_id
            WHERE s.stop_id = ? AND ro.route_short_name = ? AND st.arrival_time > ?
            ORDER BY st.arrival_time ASC
            LIMIT 1
            """, (stop_id, short_name, current_time))

        rows = cur.fetchall()

        self.close_connection(conn)
        return rows

database = Database()