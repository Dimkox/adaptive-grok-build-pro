# Writer observations

The initial negative schema fixture assumed `anyOf` was unsupported without checking the current supported-key inventory; its accepted result correctly exposed that fixture error. Use an actual unsupported keyword (`patternProperties`) and keep valid union behavior unchanged.
