'''
Created on 21.07.2014

@author: Reinhard Kreim
'''


import sqlite3
import requests

try:
    # start sqlite connection
    con = sqlite3.connect('mod.db')
    cursor = con.cursor()
    
    # function to print a specific selection menu
    def print_menu(items):
        for item in items:
            print(str(items.index(item) + 1) + ")" + " " + item)
        # add a "back" option to each menu
        print(str(len(items) +1) + ")" + " back")
            
    # drop tables with a specific prefix
    def drop_table(prefix):
        # get all tables with prefix from db
        cursor.execute('SELECT name FROM sqlite_master WHERE TYPE = "table" AND name LIKE "' + prefix + '%"')
        drop_table = cursor.fetchall()
        for drop in drop_table:
            cursor.execute('DROP TABLE ' + drop[0] + ';')
    
    # update all databases
    def update_db():
        # drop all non essential tables
        drop_table("copy_")
        drop_table("new_")
        drop_table("upd_")
        
        # dict for looking up mc versions (i.e. 1_4_6 is 1.4.6)
        version_dict = {}
        
        # create a table to store all mc versions
        cursor.execute('CREATE TABLE IF NOT EXISTS mc_versions (version TEXT PRIMARY KEY);')
        
        # get all mc versions from NEM json interface
        request_versions = requests.get('http://bot.notenoughmods.com/?json')
        versions = request_versions.json()
        
        # create version entry in table
        copy_versions = list(versions)
        for version in copy_versions:
            versions[copy_versions.index(version)] = "mc_" + version.replace(".", "_").replace("-", "_")
            
            # fill the version dict with data
            version_dict["mc_" + version.replace(".", "_").replace("-", "_")] = version
        
        # add current versions to versions table
        for version in versions:
            cursor.execute('INSERT OR IGNORE INTO mc_versions (version) VALUES (?);', (version,))
        
        # remove versions that are no longer listed at NEM
        get_versions = cursor.execute('SELECT * FROM mc_versions;')
        stored_versions = get_versions.fetchall()
        
        for stored in stored_versions:
            if stored[0] not in versions:
                # remove version from versions table
                cursor.execute('DELETE FROM mc_versions WHERE version =?;', (stored[0],))
                
                # drop version corresponding table
                cursor.execute('DROP TABLE IF EXISTS ?;', (stored[0],))
        
        # get all stored version numbers
        get_versions = cursor.execute('SELECT * FROM mc_versions;')
        stored_versions = get_versions.fetchall()
        
        # for each version create a table
        for stored in stored_versions:
            cursor.execute('CREATE TABLE IF NOT EXISTS ' + stored[0] + ' (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, longurl TEXT, shorturl TEXT, aliases TEXT, comment TEXT, modid TEXT, dev TEXT, author TEXT, lastupdated TEXT, prevversion TEXT, dependencies TEXT, version TEXT, mod_license TEXT, my_mod INTEGER);')
            
            # create a copy of the current versions mods
            cursor.execute('CREATE TABLE copy_' + stored[0] + ' AS SELECT * FROM ' + stored[0] + ';')
            
            # get the mods from NEM json interface for the corresponding version
            request_mods = requests.get('http://bot.notenoughmods.com/' + version_dict[stored[0]] + '.json')
            mods = request_mods.json()
            
            # get all modnames stored in DB
            get_db = cursor.execute('SELECT name FROM ' + stored[0] + ';')
            db_modnames = get_db.fetchall()
            
            # insert and update mods in version table
            current_mods = []   
            for this_mod in mods:
                if this_mod in db_modnames:
                    cursor.execute('UPDATE ' + stored[0] + ' SET longurl = ?, shorturl = ?, aliases = ?, comment = ?, modid = ?, dev = ?, author = ?, lastupdated = ?, prevversion = ?, dependencies = ?, version = ?, mod_license = ? WHERE name = ?;', (this_mod["longurl"], this_mod["shorturl"], str(this_mod["aliases"]), this_mod["comment"], this_mod["modid"], this_mod["dev"], this_mod["author"], this_mod["lastupdated"], this_mod["prevversion"], str(this_mod["dependencies"]), this_mod["version"], this_mod["license"], this_mod["name"] ))
                else:
                    cursor.execute('INSERT OR IGNORE INTO ' + stored[0] + '(name, longurl, shorturl, aliases, comment, modid, dev, author, lastupdated, prevversion, dependencies, version, mod_license, my_mod) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?);', (this_mod["name"], this_mod["longurl"], this_mod["shorturl"], str(this_mod["aliases"]), this_mod["comment"], this_mod["modid"], this_mod["dev"], this_mod["author"], this_mod["lastupdated"], this_mod["prevversion"], str(this_mod["dependencies"]), this_mod["version"], this_mod["license"], 0))
                
                # remember added mods
                current_mods.append(this_mod["name"])
           
            # get only the names of all current stored mods
            cursor.execute('SELECT name FROM ' + stored[0] + ';')
            db_mods = cursor.fetchall()
            
            # remove mods no longer listed at NEM
            for mod in db_mods:
                if mod[0] not in current_mods:
                    cursor.execute('DELETE FROM ' + stored[0] + ' WHERE name = ?', (mod[0],))        
                     
            # create table of new mods
            cursor.execute('CREATE TABLE new_' + stored[0] + ' AS SELECT * FROM ' + stored[0] + ' LEFT JOIN copy_' + stored[0] + ' ON (' + stored[0] + '.name = copy_' + stored[0] + '.name) WHERE copy_' + stored[0] + '.name IS NULL;')
            
            # create table of updated mods    
            cursor.execute('CREATE TABLE upd_' + stored[0] + ' AS SELECT * FROM ' + stored[0] + ' INNER JOIN copy_' + stored[0] + ' ON (' + stored[0] + '.name = copy_' + stored[0] + '.name) WHERE ' + stored[0] + '.version != copy_' + stored[0] + '.version AND ' + stored[0] + '.my_mod = "1";')
            
        # write all changes to db
        con.commit()
        
    # main menu
    def main_menu():
        while True:
            main_items =["update","select version"]
            print_menu(main_items)
            choice = input()
            
            if choice == "1":
                update_db()
            elif choice == "2":
                select_version()
            elif choice == "3":
                return
            else:
                print("Not a valid choice")
    
    # version select submenu
    def select_version():
        while True:
            # get all current mc versions from db
            cursor.execute('SELECT version FROM mc_versions')
            versions = cursor.fetchall()
            version_items = []
            
            # print a menu for each version
            for version in versions:
                version_items.append(version[0])
            print_menu(version_items)
                    
            choice = input()
            
            # add option for each version
            for version in version_items:
                if choice == str(version_items.index(version) +1):
                    version_menu(version)
            
            # add back option
            if choice == str(len(version_items) +1):
                return
                        
    # write specific mods to a html file
    def display_mods(specifier, html_name, version, where=""):
        try:
            # open file to write in
            with open("display_mods_" + html_name + version + ".html", "w", encoding='utf-8') as file:
                file.write("<html> <meta charset=\"UTF-8\"> <h1>" + version + "</h1><table>")
                
                # select mod dataset to write to file
                cursor.execute('SELECT * FROM ' + specifier + version + where +';')
                display = cursor.fetchall()
                
                # write a html table, 1 line per mod 
                for mod in display:
                    file.write("<tr>")
                    
                    for item in mod:
                        item_value = str(item)
                        if mod.index(item) == 2:
                            file.write('<td><a href="' + item_value + '">' + item_value + '</a></td>')
                        else:
                            file.write("<td>" + item_value + "</td>")
                            
                    file.write("</tr>")
                    
                file.write("</table></html>")
                
        except IOError as err:
            print('File error: ' + str(err))
        
    # add or remove a mod to my_mods
    def add_remove_mod(version, action):
        print("Add or remove mod, mod id's seperated by space")
        choice = input()
        to_add = choice.split(" ")
        for mod in to_add:
            cursor.execute('UPDATE OR FAIL ' + version + ' SET my_mod = "' + str(action) + '" WHERE id = ' + mod + ';')
        
        # write all changes to db
        con.commit()
        return
    
    # version specific submenu
    def version_menu(version):
        while True:
            version_items =["display","new mods","my mods","display new versions","add mod","remove mod"]
            print_menu(version_items)
            choice = input()
            
            if choice == "1":
                display_mods("", "", version) 
            elif choice == "2":
                display_mods("new_", "new_", version)
            elif choice == "3":
                display_mods("", "my_mods_", version, ' WHERE my_mod = "1" ')
            elif choice == "4":
                display_mods("upd_","upd_", version)
            elif choice == "5":
                add_remove_mod(version, 1)
            elif choice == "6":
                add_remove_mod(version, 0)
            elif choice == "7":
                return
            else:
                print("Not a valid choice")
               
    # start program
    main_menu()
    
except sqlite3.Error as err:
    print('DB connection error: ' + str(err))
    
finally:
    if 'con' in locals():
        con.close()