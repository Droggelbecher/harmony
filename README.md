
# Harmony

![](/docs/wa.png)

Harmony is a tool for synchronizing a repository of files between multiple
locations in scenarios where there is not necessarily a single location that
has all the files and still consistency is an issue.

Harmony is inspired by [git-annex](https://git-annex.branchable.com/),
but strives to be a lot more
straight-forward/simple both in terms of implementation as in use.

## What kind of problem does Harmony solve?

As an example, consider a large collection of media files (music, videos,
large binary asset files for a software development project)
shared across different machines.  In particular lets consider the
following challenges that can occur in this scenario:

 * There might **not be a single machine having all the files**, yet when a file
   is changed (eg. you correct the author name in a music files metadata),
   that change should be reflected on other devices.
   The same should hold through for renaming/moving of files.

 * Machines might **not be online when you make a change**, that means
   synchronization might be delayed for long periods of time which can lead to
   changes to the same file happening at different places in parallel.

 * **Files may be large**. That is, transfer of files should only happen when it
   is really requested and thus be independent from state synchronizatio.

 * There is **no single master location** which is the only one where files
   will be renamed/restructured/changed while all others just read from it.
   Everyone that has some of the files should be able to work on the naming
   and directory structure, possibly in conflicting ways in parallel (which of
   course might require later conflict resolution).


## Maturity

Harmony is in an early stage of development. We have the first tests
passing for local file synchronization, but the code is still subject to major
changes and there is some work to be done before this is useful for productive
use.

If you want to play around with it and possibly contribute, check it out and
I'll be happy to assist, but under no circumstances use it on your files
without making a backup first.


## How does this compare to git-annex/unison/...?


Tool                                             | Complete History | Handles large files well | Partial Checkouts | Feature-Richness
-----                                            |------------------|--------------------------|-----------------  |-------
VCS (like Git)                                   | Yes              | No                       | No  |
VCS LFS extensions (like Git LFS)                | Yes              | Yes                      | No  |
Git Annex                                        | Yes              | Yes                      | Yes | Feature-rich / complex
Boar                                             | Yes              | Yes                      | No  | ?
Directory Synchronizers (like Unison, Syncthing) | No               | Yes                      | No  | 
Harmony                                          | No               | Yes                      | Yes | Lean / "KISS"


### Git Annex

Harmony was inspired by Git Annex but strives to be simpler. Git Annex is very
powerful and feature rich by building on Git and providing a large variety of
synchronization protocols, a daemon that keeps watch for file changes and
other useful extensions.  Harmony is built from scratch and follows more of a
"keep it simple" / "do one thing well" approach.

### Unison

[Unison](https://www.cis.upenn.edu/~bcpierce/unison/) is a tool that allows
synchronizing two repositories with some cleverness such as tracking changes
and thus automatically choosing the newer version, asking the user what to do
in case of conflicts.  In contrast to Unison, Harmony does not yet have a GUI
but only a command line interface. Unison however is geared towards
point-to-point synchronization and can not provide a consistent repository
view if files are scattered across multiple locations.

## Further Reading

[Harmony Concepts](/docs/concepts.md)


