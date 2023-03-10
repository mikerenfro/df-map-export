-- Export diggable parts of map elevations to text files
--[====[

export-diggable-areas
=============
Export map elevations to text files, with diggable areas marked as
'1', and other areas marked as '0'.

]====]

local tm = require('tile-material')
local utils = require('utils')

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

-- from quickfort
local hard_natural_materials = utils.invert({
    df.tiletype_material.STONE,
    df.tiletype_material.FEATURE,
    df.tiletype_material.LAVA_STONE,
    df.tiletype_material.MINERAL,
    df.tiletype_material.FROZEN_LIQUID,
})
local function is_hard(tileattrs)
    -- from quickfort
    return hard_natural_materials[tileattrs.material]
end
local function is_wall(tileattrs)
    -- from quickfort
    return tileattrs.shape == df.tiletype_shape.WALL
end
local function is_tree(tileattrs)
    -- from quickfort
    return tileattrs.material == df.tiletype_material.TREE
end
local function is_water(tileattrs)
    return (tileattrs.material == df.tiletype_material.BROOK) or (tileattrs.material == df.tiletype_material.POOL) or (tileattrs.material == df.tiletype_material.FROZEN_LIQUID)
end
local function is_boulder(tileattrs)
    return tileattrs.shape == df.tiletype_shape.BOULDER
end
local function is_diggable_wall(tileattrs)
    if is_wall(tileattrs) then
        if not is_tree(tileattrs) then
            return true
        end
    end
    return false
end
local function is_visible(x, y, z)
    return dfhack.maps.isTileVisible(x, y, z)
end

local function z_to_elevation(z)
    return z+df.global.world.map.region_z-100
end

local function elevation_to_z(elevation)
    return elevation-(df.global.world.map.region_z-100)
end

local function scan_elevations()
    print("Scanning all elevations")
    rows, cols, layers = dfhack.maps.getTileSize()
    -- print(rows, cols, layers)
    mt = {}          -- create the matrix
    for i=0, rows-1 do
        mt[i] = {}     -- create a new layer
        for j=0, cols-1 do
            mt[i][j] = {} -- create a new row
            for k=0, layers-1 do
                -- print(i, j, k)
                tileattrs = df.tiletype.attrs[dfhack.maps.getTileType(j, i, k)]
                if not is_visible(j, i, k) then
                    mt[i][j][k] = '?'
                elseif (is_diggable_wall(tileattrs) and is_hard(tileattrs)) then
                    mt[i][j][k] = 'r'
                elseif (is_diggable_wall(tileattrs) and not is_hard(tileattrs)) then
                    mt[i][j][k] = 's'
                elseif is_tree(tileattrs) then
                    mt[i][j][k] = 'T'
                elseif is_water(tileattrs) then
                    mt[i][j][k] = '~'
                elseif is_boulder(tileattrs) then
                    mt[i][j][k] = 'B'
                else
                    mt[i][j][k] = 0
                end
            end
        end
    end
    return mt
end

local function find_ground_layers()
    -- Keep track of elevations with diggable tiles
    ground_layers = {}
    for k=layers-1, 0, -1 do
        -- Go through each elevation looking for diggable wall tiles
        ground_layers[k] = false
        for i=0, rows-1 do
            if ground_layers[k] == false then
                for j=0, cols-1 do
                    -- j, i since (y, x) matches (row, col)
                    tileattrs = df.tiletype.attrs[dfhack.maps.getTileType(j, i, k)]
                    if is_diggable_wall(tileattrs) then
                        if ground_layers[k] == false then
                            ground_layers[k] = true
                            break
                        end
                    end
                end
            else
                break
            end
        end
    end
    return ground_layers
end

local function find_visible_layers()
    -- Keep track of elevations with visible tiles
    visible_layers = {}
    for k=layers-1, 0, -1 do
        -- Go through each elevation looking for diggable wall tiles
        visible_layers[k] = false
        for i=0, rows-1 do
            if visible_layers[k] == false then
                for j=0, cols-1 do
                    if is_visible(j, i, k) then
                        visible_layers[k] = true
                        break
                    end
                end
            else
                break
            end
        end
    end
    return visible_layers
end

local function export_diggable_areas()
    -- print(dump(tm))
    -- print(dump(tm.GetTileMat(100,100,100)))
    -- Determine embark map size, create 3D table for holding map data
    mt = scan_elevations()
    visible_layers = find_visible_layers()
    ground_layers = find_ground_layers()
    if mode == 'nospoilers' then
        print('Finding elevations with both visible and diggable areas:')
    else
        print('Finding elevations with both visible and diggable areas (including fully-subterranean levels):')
    end
    for k=layers-1, 0, -1 do
        if mode == 'nospoilers' then
            vis_check = (visible_layers[k] == true)
        else
            vis_check = true
        end
        if vis_check then
            if ground_layers[k] == true then
                local filename = string.format("elevation-%+04d.txt", z_to_elevation(k))
                local f = assert(io.open(filename, 'w'))
                print('Elevation ' .. z_to_elevation(k))
                -- io.stdout:write(string.format('%d ', z_to_elevation(k)))
                -- io.stdout:flush()
                for i=0, rows-1 do
                    row_string = ''
                    for j=0, cols-1 do
                        -- mat = tm.GetTileMat(j,i,k)
                        -- matmode = mat['mode']
                        -- print(i, j, k, dump(mat[matmode]['flags']))
                        -- print(i, j, k, dump(matmode))
                        row_string = row_string .. mt[i][j][k]
                    end
                    -- print(row_string)
                    f:write(row_string..'\n')
                end
                f:close()
            end
        else
            -- io.stdout:write('\n')
            print('Exiting at elevation '.. z_to_elevation(k) .. ' to avoid spoilers')
            break
        end
    end
end

export_diggable_areas(...)
