from mceditlib.worldeditor import WorldEditor
import numpy



def test_relight(schematic_world, pc_world):
    anvilDim = pc_world.getDimension()
    bounds = anvilDim.bounds
    point = bounds.origin + (bounds.size * (0.5, 0.5, 0.5))

    box = bounds.expand(-100, 0, -100)

    chunks = [(cx, cz) for cx, cz in anvilDim.chunkPositions() if (cx << 4, 1, cz << 4) not in box]
    for c in chunks:
        anvilDim.deleteChunk(*c)

    stationDim = schematic_world.getDimension()
    anvilDim.copyBlocks(stationDim, stationDim.bounds, point, create=True)

    pc_world.saveChanges()
    cx = int(point.x + 32) >> 4
    cz = int(point.z + 32) >> 4

    def check():
        sl = numpy.sum(anvilDim.getChunk(cx, cz).SkyLight)
        bl = numpy.sum(anvilDim.getChunk(cx, cz).BlockLight)
        assert (sl, bl) == (341328, 43213)

    check()

    pc_world.close()

    pc_world = WorldEditor(pc_world.filename)
    check()

