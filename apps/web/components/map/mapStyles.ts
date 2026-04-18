export const INDIA_BOUNDS = { north: 37.6, south: 6.5, west: 68.1, east: 97.4 };

export const MAP_STYLES: google.maps.MapTypeStyle[] = [
  { elementType: "geometry",             stylers: [{ color: "#F0EEE8" }] },
  { elementType: "labels.text.stroke",   stylers: [{ color: "#F0EEE8" }] },
  { elementType: "labels.text.fill",     stylers: [{ color: "#8a8a7a" }] },
  { featureType: "water", elementType: "geometry",         stylers: [{ color: "#C8E6E3" }] },
  { featureType: "water", elementType: "labels.text.fill", stylers: [{ color: "#7BBCB8" }] },
  { featureType: "road",         elementType: "geometry",        stylers: [{ color: "#DDDBD5" }] },
  { featureType: "road",         elementType: "geometry.stroke",  stylers: [{ color: "#CCCBC5" }] },
  { featureType: "road.highway", elementType: "geometry",        stylers: [{ color: "#D4D2CC" }] },
  { featureType: "road.highway", elementType: "geometry.stroke",  stylers: [{ color: "#C4C2BC" }] },
  { featureType: "road",         elementType: "labels.text.fill", stylers: [{ color: "#9a9a8a" }] },
  { featureType: "poi",     stylers: [{ visibility: "off" }] },
  { featureType: "transit", stylers: [{ visibility: "off" }] },
  { featureType: "administrative.country",  elementType: "geometry.stroke", stylers: [{ color: "#AAAAAA" }, { weight: 1.2 }] },
  { featureType: "administrative.province", elementType: "geometry.stroke", stylers: [{ color: "#CCCCBE" }, { weight: 0.8 }] },
  { featureType: "administrative.locality", elementType: "labels.text.fill", stylers: [{ color: "#7a7a6a" }] },
  { featureType: "landscape.natural",   elementType: "geometry", stylers: [{ color: "#E8E6E0" }] },
  { featureType: "landscape.man_made",  elementType: "geometry", stylers: [{ color: "#EEECEA" }] },
];

export const MAP_OPTIONS: google.maps.MapOptions = {
  center: { lat: 22.5937, lng: 78.9629 },
  zoom: 5,
  minZoom: 4,
  maxZoom: 16,
  restriction: { latLngBounds: INDIA_BOUNDS, strictBounds: false },
  disableDefaultUI: true,
  styles: MAP_STYLES,
  gestureHandling: "greedy",
};
