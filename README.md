pyramid_debugtoolbar_dogpile
============================

dogpile caching support for pyramid_debugtoolbar

This package tracks the following dogpile api calls :

	get
	get_multi
	set
	set_multi
	delete
	delete_multi

Your pyramid_debugtoolbar will have a "Dogpile" panel that lists:

	* the number of calls (in tab header)
	* statistics on cache hits/misses/timing per api call type
	* a listing of all calls that features: call, key, hit/miss, timing
	
As of v0.1.4 you can filter the keys on the panel. yay.

This package works by wrapping requests to dogpile regions into a Proxy Backend.  This has a significant performance overhead and relies on the DEBUG ONLY `get_current_request`, so make sure that you disable this LoggingProxy on production machines.



how to use this
===============


1. update your ENVIRONMENT.ini file

	pyramid.includes = ... pyramid_debugtoolbar_dogpile


2. update your caching definition to use the proxy:

	from pyramid_debugtoolbar_dogpile import LoggingProxy as DogpileLoggingProxy


What does it look like?
=======================

The panel renders in two parts:

First Section - topline statistics

Second Section - chronological list of cache operations. API calls and results are color-coded for quick review.

![ScreenShot](https://raw.github.com/jvanasco/pyramid_debugtoolbar_dogpile/master/screenshot.png)