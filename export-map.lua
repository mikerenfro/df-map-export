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
local mode = nil
local spoilers = false
local debug = false
if args[1] == 'spoilers' then
    spoilers = true
end
if args[2] == 'debug' then
    debug = true
end

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

local function is_boulder(tileattrs)
    return tileattrs.shape == df.tiletype_shape.BOULDER
end

local function is_tree(tileattrs)
    -- from quickfort
    return tileattrs.material == df.tiletype_material.TREE
end

local function is_wall(tileattrs)
    -- from quickfort
    return tileattrs.shape == df.tiletype_shape.WALL
end

local function is_diggable_wall(tileattrs)
    if is_wall(tileattrs) then
        if not is_tree(tileattrs) then
            return true
        end
    end
    return false
end

local function is_hard(tileattrs)
    -- from quickfort
    return hard_natural_materials[tileattrs.material]
end

local function is_visible(x, y, z)
    return dfhack.maps.isTileVisible(x, y, z)
end

local function is_magma(tileflags)
    return tileflags.liquid_type and (tileflags.flow_size > 0)
end

local function is_water(tileattrs)
    return (tileattrs.material == df.tiletype_material.RIVER) or (tileattrs.material == df.tiletype_material.BROOK) or (tileattrs.material == df.tiletype_material.POOL) or (tileattrs.material == df.tiletype_material.FROZEN_LIQUID)
end

local function is_grass(tileattrs)
    return (tileattrs.material == df.tiletype_material.GRASS_LIGHT) or (tileattrs.material == df.tiletype_material.GRASS_DARK) or (tileattrs.material == df.tiletype_material.GRASS_DRY) or (tileattrs.material == df.tiletype_material.GRASS_DEAD)
end

local function is_plant(tileattrs)
    return (tileattrs.material == df.tiletype_material.PLANT)
end

local function is_soil_floor_or_ramp(tileattrs)
    return ((tileattrs.shape == df.tiletype_shape.FLOOR) or (tileattrs.shape == df.tiletype_shape.RAMP)) and (tileattrs.material == df.tiletype_material.SOIL)
end

local function is_stone_floor_or_ramp(tileattrs)
    return ((tileattrs.shape == df.tiletype_shape.FLOOR) or (tileattrs.shape == df.tiletype_shape.RAMP)) and (tileattrs.material == df.tiletype_material.STONE)
end

local function is_pebbles(tileattrs)
    return (tileattrs.shape == df.tiletype_shape.PEBBLES)
end

local function z_to_elevation(z)
    return z+df.global.world.map.region_z-100
end

local function elevation_to_z(elevation)
    return elevation-(df.global.world.map.region_z-100)
end

local function classify_tile(x, y, z, spoilers)
    -- print(x, y, z, dfhack.maps.getTileType(x, y, z))
    -- if z == 3 then
    --     print('At (x, y, z)=(' .. x .. ',' .. y .. ',' .. z .. '), getTileType(x, y, z) = ' .. dfhack.maps.getTileType(x, y, z))
    -- end
    local tileattrs = nil
    if dfhack.maps.getTileType(x, y, z) == nil then
        return '!'
    else
        tileattrs = df.tiletype.attrs[dfhack.maps.getTileType(x, y, z)]
        tileflags = dfhack.maps.getTileFlags(x, y, z)
    end
    if not is_visible(x, y, z) and not spoilers then
        return '?'
    elseif is_magma(tileflags) then
        return 'M'
    elseif is_water(tileattrs) then
        return '~'
    elseif is_grass(tileattrs) then
        return 'g'
    elseif is_plant(tileattrs) then
        return 'p'
    elseif (is_diggable_wall(tileattrs) and not is_hard(tileattrs)) or is_soil_floor_or_ramp(tileattrs) then
        return 's'
    elseif is_tree(tileattrs) then
        return 'T'
    elseif is_boulder(tileattrs) then
        return 'B'
    elseif (is_diggable_wall(tileattrs) and is_hard(tileattrs)) or is_stone_floor_or_ramp(tileattrs) or is_pebbles(tileattrs) then
        return 'r'
    else
        return ' '
    end

end

local function export_one_z_level(folder, z, vis_check, spoilers)
    local spoilers_str = 'false'
    local vis_check_str = 'false'
    if spoilers == true then
        spoilers_str = 'true'
    end
    if vis_check == true then
        local vis_check_str = 'true'
    end
    -- print ('spoilers = ' .. spoilers_str .. ', vis_check = ' .. vis_check_str)
    if spoilers or vis_check then
        print('Exporting z-level ' .. z .. ' (elevation '.. z_to_elevation(z) .. ')')
        local xmax, ymax, _ = dfhack.maps.getTileSize()
        local elevation = z_to_elevation(z)
        local fortress_name = dfhack.TranslateName(df.global.world.world_data.active_site[0].name)
        local filename = string.format("%s/%s-%+04d.txt", folder, fortress_name, elevation)
        local f = assert(io.open(filename, 'w'))
        for y=0, ymax-1 do
            local row_string = ''
            for x=0, xmax-1 do
                local classification = classify_tile(x, y, z, spoilers)
                row_string = row_string .. classification
            end
            f:write(row_string..'\n')
        end
        f:close()
    end
end

local function find_ground_layers()
    xmax, ymax, zmax = dfhack.maps.getTileSize()
    -- Keep track of elevations with diggable tiles
    local ground_layers = {}
    for z=zmax-1, 0, -1 do
        -- Go through each elevation looking for diggable wall tiles
        ground_layers[z] = false
        for y=0, ymax-1 do
            if ground_layers[z] == false then
                for x=0, xmax-1 do
                    -- j, i since (y, x) matches (row, col)
                    local tiletype = dfhack.maps.getTileType(x, y, z)
                    if tiletype ~= nil then
                    -- status, err = pcall(function() tileattrs = df.tiletype.attrs[dfhack.maps.getTileType(x, y, z)] end)
                    -- if status then
                        tileattrs = df.tiletype.attrs[dfhack.maps.getTileType(x, y, z)]
                        if is_diggable_wall(tileattrs) then
                            if ground_layers[z] == false then
                                ground_layers[z] = true
                                break
                            end
                        end
                    -- else
                    --     print('At (x,y,z)=('..x..','..y..','..z..'), tiletype was nil')
                    end
                end
            else
                break
            end
        end
        if debug then
            if ground_layers[z] then
                print('Checked z-level '..z..', (elevation '..z_to_elevation(z)..'), ground_layers[z]=true')
            else
                print('Checked z-level '..z..', (elevation '..z_to_elevation(z)..'), ground_layers[z]=false')
            end
        end
    end
    return ground_layers
end

local function find_visible_layers()
    xmax, ymax, zmax = dfhack.maps.getTileSize()
    -- Keep track of elevations with visible tiles
    local visible_layers = {}
    for z=zmax-1, 0, -1 do
        -- Go through each elevation looking for vislble tiles
        visible_layers[z] = false
        for y=0, ymax-1 do
            if visible_layers[z] == false then
                for x=0, xmax-1 do
                    if is_visible(x, y, z) then
                        visible_layers[z] = true
                        break
                    end
                end
            else
                break
            end
        end
        if debug then
            if visible_layers[z] then
                print('Checked z-level '..z..', (elevation '..z_to_elevation(z)..'), visible_layers[z]=true')
            else
                print('Checked z-level '..z..', (elevation '..z_to_elevation(z)..'), visible_layers[z]=false')
            end
        end
    end
    return visible_layers
end

local function export_map_elevations()
    _, _, zmax = dfhack.maps.getTileSize()
    if debug then
        print('find_ground_layers()')
    end
    local ground_layers = find_ground_layers()
    -- if debug then
    --     print('ground_layers = ')
    --     print(dump(ground_layers))
    -- end
    if debug then
        print('find_visible_layers()')
    end
    local visible_layers = find_visible_layers()
    if spoilers then
        print('Finding elevations with diggable areas (including fully-subterranean levels):')
    else
        print('Finding elevations with both visible and diggable areas:')
    end

    local df_path = dfhack.getDFPath()
    local export_path = "map-exports/" .. dfhack.TranslateName(df.global.world.world_data.active_site[0].name)
    dfhack.filesystem.mkdir_recursive(export_path)


    for z=zmax-1, 0, -1 do
        if ground_layers[z] or ground_layers[z-1] then
            export_one_z_level(export_path, z, visible_layers[z], spoilers)
        end
    end
    print("Map export files can be found in Dwarf Fortress folder under "..export_path)
end

export_map_elevations(...)
