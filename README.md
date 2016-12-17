

Harmony is a tool for synchronizing a repository of files between multiple
locations in scenarios where there is not necessarily a single location that
has all the files and still consistency is an issue.

Harmony is inspired by git-annex (TODO: link), but strives to be a lot more
straight-forward/simple both in terms of implementation as in use.

== What kind of problem does this solve?

As an example, consider a large collection of media files (music, videos)
shared across different machines.  Of course, Harmony can be used for all
kinds of files, this is just an example.  In particular lets consider the
following problems that can occur in this scenario:

 * There might *not be a single machine having all the files*, yet when a file
   is changed (eg. you correct the author name in a music files metadata),
   that change should be reflected on other devices.
   The same should hold through for renaming/moving of files.

 * Machines might *not be online when you make a change*, that means
   synchronization might be delayed for long periods of time which can lead to
   changes to the same file happening at different places in parallel.

 * *Files may be large*. That is, transfer of files should only happen when it
   is really requested and thus be independent from state synchronization.

 TODO: Extend

== Maturity

Harmony is in an early stage of development. We have the first unittests
passing for local file synchronization, but the code is not stable and no
remote synchronization is implemented yet.

If you want to play around with it and possibly contribute, check it out and
I'll be happy to assist, but do not use it on your files without making a
backup first.


== How does this compare to git-annex/unison/...?

=== Git Annex

Harmony was inspired by Git Annex but strives to be simpler. Git Annex is very
powerful and feature rich by building on Git and providing a large variety of
synchronization protocols, a daemon that keeps watch for file changes and
other useful extensions.  Harmony is built from scratch and follows more of a
"keep it simple" / "do one thing well" approach.

=== Unison

Unison is a tool that allows synchronizing two repositories with some
cleverness such as tracking changes and thus automatically choosing the newer
version, asking the user what to do in case of conflicts.
In contrast to Unison, Harmony does not yet have a GUI but only a command line
interface. Unison however is geared towards point-to-point synchronization and
can not provide a consistent repository view if files are scattered across
multiple locations.


