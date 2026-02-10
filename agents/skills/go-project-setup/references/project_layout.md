Source: https://go.dev/doc/modules/layout\n\n# Organizing a Go module\n\n\n# Organizing a Go module\n\nA common question developers new to Go have is “How do I organize my Go
project?”, in terms of the layout of files and folders. The goal of this
document is to provide some guidelines that will help answer this question. To
make the most of this document, make sure you’re familiar with the basics of Go
modules by reading the tutorial and
managing module source.\n\nGo projects can include packages, command-line programs or a combination of the
two. This guide is organized by project type.\n\n### Basic package\n\nA basic Go package has all its code in the project’s root directory. The project
consists of a single module, which consists of a single package. The package
name matches the last path component of the module name. For a very simple
package requiring a single Go file, the project structure is:\n\n```\nproject-root-directory/
  go.mod
  modname.go
  modname_test.go
\n```\n\n[throughout this document, file/package names are entirely arbitrary]\n\nAssuming this directory is uploaded to a GitHub repository at
github.com/someuser/modname, the module line in the go.mod file should say
module github.com/someuser/modname.\n\nThe code in modname.go declares the package with:\n\n```\npackage modname

// ... package code here
\n```\n\nUsers can then rely on this package by import-ing it in their Go code with:\n\n```\nimport "github.com/someuser/modname"
\n```\n\nA Go package can be split into multiple files, all residing within the same
directory, e.g.:\n\n```\nproject-root-directory/
  go.mod
  modname.go
  modname_test.go
  auth.go
  auth_test.go
  hash.go
  hash_test.go
\n```\n\nAll the files in the directory declare package modname.\n\n### Basic command\n\nA basic executable program (or command-line tool) is structured according to its
complexity and code size. The simplest program can consist of a single Go file
where func main is defined. Larger programs can have their code split across
multiple files, all declaring package main:\n\n```\nproject-root-directory/
  go.mod
  auth.go
  auth_test.go
  client.go
  main.go
\n```\n\nHere the main.go file contains func main, but this is just a convention. The
“main” file can also be called modname.go (for an appropriate value of
modname) or anything else.\n\nAssuming this directory is uploaded to a GitHub repository at
github.com/someuser/modname, the module line in the go.mod file should
say:\n\n```\nmodule github.com/someuser/modname
\n```\n\nAnd a user should be able to install it on their machine with:\n\n```\n$ go install github.com/someuser/modname@latest
\n```\n\n### Package or command with supporting packages\n\nLarger packages or commands may benefit from splitting off some functionality
into supporting packages. Initially, it’s recommended placing such packages into
a directory named internal;
this prevents other
modules from depending on packages we don’t necessarily want to expose and
support for external uses. Since other projects cannot import code from our
internal directory, we’re free to refactor its API and generally move things
around without breaking external users. The project structure for a package is
thus:\n\n```\nproject-root-directory/
  internal/
    auth/
      auth.go
      auth_test.go
    hash/
      hash.go
      hash_test.go
  go.mod
  modname.go
  modname_test.go
\n```\n\nThe modname.go file declares package modname, auth.go declares package auth and so on. modname.go can import the auth package as follows:\n\n```\nimport "github.com/someuser/modname/internal/auth"
\n```\n\nThe layout for a command with supporting packages in an internal directory is
very similar, except that the file(s) in the root directory declare package main.\n\n### Multiple packages\n\nA module can consist of multiple importable packages; each package has its own
directory, and can be structured hierarchically. Here’s a sample project
structure:\n\n```\nproject-root-directory/
  go.mod
  modname.go
  modname_test.go
  auth/
    auth.go
    auth_test.go
    token/
      token.go
      token_test.go
  hash/
    hash.go
  internal/
    trace/
      trace.go
\n```\n\nAs a reminder, we assume that the module line in go.mod says:\n\n```\nmodule github.com/someuser/modname
\n```\n\nThe modname package resides in the root directory, declares package modname
and can be imported by users with:\n\n```\nimport "github.com/someuser/modname"
\n```\n\nSub-packages can be imported by users as follows:\n\n```\nimport "github.com/someuser/modname/auth"
import "github.com/someuser/modname/auth/token"
import "github.com/someuser/modname/hash"
\n```\n\nPackage trace that resides in internal/trace cannot be imported outside this
module. It’s recommended to keep packages in internal as much as possible.\n\n### Multiple commands\n\nMultiple programs in the same repository will typically have separate directories:\n\n```\nproject-root-directory/
  go.mod
  internal/
    ... shared internal packages
  prog1/
    main.go
  prog2/
    main.go
\n```\n\nIn each directory, the program’s Go files declare package main. A top-level
internal directory can contain shared packages used by all commands in the
repository.\n\nUsers can install these programs as follows:\n\n```\n$ go install github.com/someuser/modname/prog1@latest
$ go install github.com/someuser/modname/prog2@latest
\n```\n\nA common convention is placing all commands in a repository into a cmd
directory; while this isn’t strictly necessary in a repository that consists
only of commands, it’s very useful in a mixed repository that has both commands
and importable packages, as we will discuss next.\n\n### Packages and commands in the same repository\n\nSometimes a repository will provide both importable packages and installable
commands with related functionality. Here’s a sample project structure for such
a repository:\n\n```\nproject-root-directory/
  go.mod
  modname.go
  modname_test.go
  auth/
    auth.go
    auth_test.go
  internal/
    ... internal packages
  cmd/
    prog1/
      main.go
    prog2/
      main.go
\n```\n\nAssuming this module is called github.com/someuser/modname, users can now both
import packages from it:\n\n```\nimport "github.com/someuser/modname"
import "github.com/someuser/modname/auth"
\n```\n\nAnd install programs from it:\n\n```\n$ go install github.com/someuser/modname/cmd/prog1@latest
$ go install github.com/someuser/modname/cmd/prog2@latest
\n```\n\n### Server project\n\nGo is a common language choice for implementing servers. There is a very large
variance in the structure of such projects, given the many aspects of server
development: protocols (REST? gRPC?), deployments, front-end files,
containerization, scripts and so on. We will focus our guidance here on the
parts of the project written in Go.\n\nServer projects typically won’t have packages for export, since a server is
usually a self-contained binary (or a group of binaries). Therefore, it’s
recommended to keep the Go packages implementing the server’s logic in the
internal directory. Moreover, since the project is likely to have many other
directories with non-Go files, it’s a good idea to keep all Go commands together
in a cmd directory:\n\n```\nproject-root-directory/
  go.mod
  internal/
    auth/
      ...
    metrics/
      ...
    model/
      ...
  cmd/
    api-server/
      main.go
    metrics-analyzer/
      main.go
    ...
  ... the project's other directories with non-Go code
\n```\n\nIn case the server repository grows packages that become useful for sharing with
other projects, it’s best to split these off to separate modules.