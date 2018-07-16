
Repository
==========

A Repository is a collection of files that logically belong together in a folder structure.
Think of your music collection, photos, videos or shared data files in your company required
by various software development projects.

A key property of Harmony is the fact that its not necessary to have a location
that stores the complete repository as long as for each file there is at least one location that has it.
Of course there might be good reasons to do so anyway, but harmony will let you decide.

The repository also defines what version of a file you consider to be the most "up-to-date"
across all your storage locations.

In that sense, a repository can be thought of something rather abstract:
It is the collection of files and directories as it would look,
if you would store all of them in one physical place in the most up-to-date version.


Location
========

In contrast to the Repository which is just an abstract list of files behind it,
a Location denotes an actual place for data storage that holds some of these files
(together with the Repository list).

A location is usually a folder on some disk, pen drive or server.
Locations only interact with other locations of the same Repository.
There are two ways in which a Location can interact with another:

* Synchronizing State:
  This synchronizes meta information between Locations, that is the Repository state and information about which location has what files in what version.
  Synchronizing state is usually fast as it only transferres data *about* files (timestamps, hashes, etc...),
  but not their content.

* Synchronizing Files:
  Actually transferring files between two Locations is a seperate action. This allows you to do a (fast)
  synchronizing of state first after which you can determine which Location(s) have the most recent version of a file
  and then decide on what to download from where. 
