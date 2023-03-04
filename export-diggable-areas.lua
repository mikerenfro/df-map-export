-- Export diggable parts of map elevations to text files
--[====[

export-diggable-areas
=============
Export map elevations to text files, with diggable areas marked as
'1', and other areas marked as '0'.

]====]

local args = {...}
local mode = args[1] or 'nospoilers'

local function dump(o)
    -- https://stackoverflow.com/a/27028488
    if type(o) == 'table' then
       local s = '{ '
       for k,v in pairs(o) do
          if type(k) ~= 'number' then k = '"'..k..'"' end
          s = s .. '['..k..'] = ' .. dump(v) .. ', '
       end
       return s .. '} '
    else
       return tostring(o)
    end
end

local function is_wall(tileattrs)
    -- from quickfort
    return tileattrs.shape == df.tiletype_shape.WALL
end
local function is_tree(tileattrs)
    -- from quickfort
    return tileattrs.material == df.tiletype_material.TREE
end
local function is_diggable_wall(tileattrs)
    if is_wall(tileattrs) then
        if not is_tree(tileattrs) then
            return true
        end
    end
    return false
end

local function export_diggable_areas()
    -- Determine embark map size, create 3D table for holding map data
    rows, cols, layers = dfhack.maps.getTileSize()
    -- print(rows, cols, layers)
    mt = {}          -- create the matrix
    for i=0, rows-1 do
        mt[i] = {}     -- create a new layer
        for j=0, cols-1 do
            mt[i][j] = {} -- create a new row
            for k=0, layers-1 do
                -- print(i, j, k)
                mt[i][j][k] = 0
            end
        end
    end
    -- Keep track of elevations with a mix of visible and diggable tiles
    visible_layers = {}
    ground_layers = {}
    for k=layers-1, 0, -1 do
        -- Go through each elevation looking for diggable wall tiles
        visible_layers[k] = false
        ground_layers[k] = false
        for i=0, rows-1 do
            for j=0, cols-1 do
                -- j, i since (y, x) matches (row, col)
                tileattrs = df.tiletype.attrs[dfhack.maps.getTileType(j, i, k)]
                if is_diggable_wall(tileattrs) then
                    mt[i][j][k] = 1
                    ground_layers[k] = true
                else
                    visible_layers[k] = true
                end
            end
        end
    end
    -- print(dump(visible_layers))
    if mode == 'nospoilers' then
        print('Finding elevations with both visible and diggable areas:')
    else
        print('Finding elevations with both visible and diggable areas (including fully-subterranean levels):')
    end
    for k=layers-1, 0, -1 do
        if mode == 'nospoilers' then
            if visible_layers[k] == true then
                if ground_layers[k] == true then
                    local filename = string.format("elevation-%+04d.txt", k-127)
                    local f = assert(io.open(filename, 'w'))
                    print('Elevation ' .. k-127)
                    -- io.stdout:write(string.format('%d ', k-127))
                    -- io.stdout:flush()
                    for i=0, rows-1 do
                        row_string = ''
                        for j=0, cols-1 do
                            row_string = row_string .. mt[i][j][k]
                        end
                        -- print(row_string)
                        f:write(row_string..'\n')
                    end
                    f:close()
                end
            else
                -- io.stdout:write('\n')
                print('Exiting at elevation '.. (k-127) .. ' to avoid spoilers')
                break
            end
        else
            if ground_layers[k] == true then
                local filename = string.format("elevation-%+04d.txt", k-127)
                local f = assert(io.open(filename, 'w'))
                print('Elevation ' .. k-127)
                -- io.stdout:write(string.format('%d ', k-127))
                -- io.stdout:flush()
                for i=0, rows-1 do
                    row_string = ''
                    for j=0, cols-1 do
                        row_string = row_string .. mt[i][j][k]
                    end
                    -- print(row_string)
                    f:write(row_string..'\n')
                end
                f:close()
            end
        end
    end
end

export_diggable_areas(...)
