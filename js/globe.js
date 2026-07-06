const CONFIG_URL = "data/regions.json";
const LAND_URL = "https://cdn.jsdelivr.net/npm/world-atlas@2/land-110m.json";

const svg = d3.select("#globe");
const tooltip = d3.select("#tooltip");
const width = 900, height = 900;

let baseScale = 390, currentScale = baseScale;
let spinning = false, spinTimer = null;
let rotation = [75, -68, 0], targetRotation = [75, -68, 0], smoothTimer = null;
let landData = null, regions = [];

const projection = d3.geoOrthographic()
  .scale(currentScale)
  .translate([width / 2, height / 2])
  .rotate(rotation)
  .clipAngle(90);

const path = d3.geoPath(projection);
const graticule = d3.geoGraticule10();
const sphere = { type: "Sphere" };

const arcticCircle = {
  type: "LineString",
  coordinates: d3.range(-180, 181, 1).map(lon => [lon, 66.5636])
};

const g = svg.append("g");

g.append("path").datum(sphere).attr("class", "sphere");
g.append("path").datum(graticule).attr("class", "graticule");

const defs = svg.select("defs");

const landClip = defs.append("clipPath").attr("id", "landClip");
const landClipPath = landClip.append("path");

const landBasePath = g.append("path").attr("class", "land-base");
const flagGroup = g.append("g").attr("clip-path", "url(#landClip)");
const outlineGroup = g.append("g").attr("clip-path", "url(#landClip)");
const landOutlinePath = g.append("path").attr("class", "land-outline");
const arcticPath = g.append("path").datum(arcticCircle).attr("class", "arctic-circle");

function reverseGeoJSONRings(obj) {
  const copy = JSON.parse(JSON.stringify(obj));

  function reverseGeometry(geom) {
    if (!geom) return;

    if (geom.type === "Polygon") {
      geom.coordinates = geom.coordinates.map(ring => [...ring].reverse());
    } else if (geom.type === "MultiPolygon") {
      geom.coordinates = geom.coordinates.map(poly =>
        poly.map(ring => [...ring].reverse())
      );
    } else if (geom.type === "GeometryCollection") {
      geom.geometries.forEach(reverseGeometry);
    }
  }

  if (copy.type === "FeatureCollection") {
    copy.features.forEach(f => reverseGeometry(f.geometry));
  } else if (copy.type === "Feature") {
    reverseGeometry(copy.geometry);
  } else {
    reverseGeometry(copy);
  }

  return copy;
}

function normalizeLon(lon) {
  return ((lon + 180) % 360 + 360) % 360 - 180;
}

function clampLat(lat) {
  return Math.max(-89.5, Math.min(89.5, lat));
}

function showTooltip(event, region) {
  tooltip
    .style("display", "block")
    .style("left", `${event.clientX + 14}px`)
    .style("top", `${event.clientY + 14}px`)
    .html(`<strong>${region.name}</strong><span>Click to play the current challenge</span>`);
}

function hideTooltip() {
  tooltip.style("display", "none");
}

function redraw() {
  g.select(".sphere").attr("d", path);
  g.select(".graticule").attr("d", path);

  if (landData) {
    landBasePath.datum(landData).attr("d", path);
    landOutlinePath.datum(landData).attr("d", path);
    landClipPath.datum(landData).attr("d", path);
  }

  regions.forEach(region => {
    const d = path(region.geojson);

    region.clipPath.attr("d", d);
    region.outlinePath.datum(region.geojson).attr("d", d);

    // Important :
    // on ne recalcule plus x/y/width/height du drapeau ici.
    // Le drapeau reste fixe dans le SVG, seulement le clip bouge avec la région.
  });

  arcticPath.attr("d", path);
}

function applyRotation(r) {
  rotation = [normalizeLon(r[0]), clampLat(r[1]), 0];
  projection.rotate(rotation);
  hideTooltip();
  redraw();
}

function startSmoothLoop() {
  if (smoothTimer) return;

  smoothTimer = d3.timer(() => {
    const ease = 0.18;

    let lonDiff = targetRotation[0] - rotation[0];
    if (lonDiff > 180) lonDiff -= 360;
    if (lonDiff < -180) lonDiff += 360;

    const latDiff = targetRotation[1] - rotation[1];

    if (Math.abs(lonDiff) < 0.01 && Math.abs(latDiff) < 0.01) {
      applyRotation(targetRotation);
      smoothTimer.stop();
      smoothTimer = null;
      return;
    }

    applyRotation([
      rotation[0] + lonDiff * ease,
      rotation[1] + latDiff * ease,
      0
    ]);
  });
}

function setTargetRotation(r) {
  targetRotation = [normalizeLon(r[0]), clampLat(r[1]), 0];
  startSmoothLoop();
}

function setView(view) {
  const views = {
    arctic: [0, -90, 0],
    canada: [75, -68, 0]
  };

  setTargetRotation(views[view] || views.canada);
}

function toggleSpin() {
  spinning = !spinning;

  if (spinning) {
    if (smoothTimer) {
      smoothTimer.stop();
      smoothTimer = null;
    }

    spinTimer = d3.timer(() => {
      targetRotation = [normalizeLon(targetRotation[0] + 0.12), targetRotation[1], 0];
      applyRotation([rotation[0] + 0.12, rotation[1], 0]);
    });
  } else if (spinTimer) {
    spinTimer.stop();
    spinTimer = null;
  }
}

let dragStart = null;
let dragStartRotation = null;

svg.call(d3.drag()
  .on("start", event => {
    if (spinning) toggleSpin();

    if (smoothTimer) {
      smoothTimer.stop();
      smoothTimer = null;
    }

    hideTooltip();
    dragStart = [event.x, event.y];
    dragStartRotation = [...rotation];
    targetRotation = [...rotation];
  })
  .on("drag", event => {
    const speed = 0.35;
    const dx = event.x - dragStart[0];
    const dy = event.y - dragStart[1];

    const newLon = dragStartRotation[0] + dx * speed;
    const newLat = dragStartRotation[1] - dy * speed;

    targetRotation = [normalizeLon(newLon), clampLat(newLat), 0];
    applyRotation(targetRotation);
  })
  .on("end", () => {
    dragStart = null;
    dragStartRotation = null;
  })
);

svg.call(d3.zoom()
  .scaleExtent([0.6, 2.2])
  .filter(event => event.type === "wheel")
  .on("zoom", event => {
    currentScale = baseScale * event.transform.k;
    projection.scale(currentScale);
    hideTooltip();
    redraw();
  })
);

svg.on("dblclick.zoom", null);
svg.on("dblclick", () => setView("canada"));

async function load() {
  const [config, world] = await Promise.all([
    d3.json(CONFIG_URL),
    d3.json(LAND_URL)
  ]);

  landData = topojson.feature(world, world.objects.land);

  for (const item of config.regions) {
    let geojson = await d3.json(item.geojson);
    if (item.needsReverse) geojson = reverseGeoJSONRings(geojson);

    const clipId = `clip-${item.id}`;

    const clipPath = defs.append("clipPath")
      .attr("id", clipId)
      .append("path");

    const flagImage = flagGroup.append("image")
      .attr("class", "region-flag")
      .attr("href", item.flag)
      .attr("clip-path", `url(#${clipId})`)
      .attr("preserveAspectRatio", "xMidYMid meet")
      .attr("x", 230)
      .attr("y", 250)
      .attr("width", 440)
      .attr("height", 300);

    const outlinePath = outlineGroup.append("path")
      .attr("class", "region-outline")
      .on("mouseenter", event => showTooltip(event, item))
      .on("mousemove", event => showTooltip(event, item))
      .on("mouseleave", hideTooltip)
      .on("click", () => {
        if (item.challenge_url) window.open(item.challenge_url, "_blank");
      });

    regions.push({
      ...item,
      geojson,
      clipPath,
      flagImage,
      outlinePath
    });
  }

  redraw();
}

load();

window.setView = setView;
window.toggleSpin = toggleSpin;
