import { create } from 'zustand';

export interface ViewState {
  longitude: number;
  latitude: number;
  zoom: number;
  pitch: number;
  bearing: number;
}

export interface DistrictInfo {
  name: string;
  crimeCount: number;
  // Issue 161: null when the backend has not supplied a model risk score.
  riskScore: number | null;
  // Issue 161: optional — only present when derivable from backend data.
  beatRatio?: number | null; // percentage coverage
  topCrimeType: string;
  weeklyTrend: 'up' | 'down' | 'stable';
}

interface MapState {
  viewState: ViewState;
  selectedDistrict: string | null;
  selectedStation: string | null;
  selectedCrimeId: string | null;
  timeOfDay: number; // 0 to 23 hours
  layers: {
    hotspot: boolean;
    beatCoverage: boolean;
    riskScore: boolean;
    socioEconomic: boolean;
  };
  districtData: Record<string, DistrictInfo>;
  setViewState: (viewState: ViewState) => void;
  setSelectedDistrict: (district: string | null) => void;
  setSelectedStation: (station: string | null) => void;
  setSelectedCrimeId: (crimeId: string | null) => void;
  setTimeOfDay: (hour: number) => void;
  toggleLayer: (layerKey: 'hotspot' | 'beatCoverage' | 'riskScore' | 'socioEconomic') => void;
  flyToDistrict: (districtName: string) => void;
}

// Coordinates for Karnataka Districts
export const DISTRICT_COORDS: Record<string, { lat: number; lng: number; zoom: number }> = {
  'Bengaluru Urban': { lat: 12.9716, lng: 77.5946, zoom: 11 },
  'Mysuru': { lat: 12.2958, lng: 76.6394, zoom: 11.5 },
  'Kalaburagi': { lat: 17.3297, lng: 76.8343, zoom: 11 },
  'Belagavi': { lat: 16.12, lng: 74.65, zoom: 11 },
  'Tumkuru': { lat: 13.3379, lng: 77.1173, zoom: 10.5 },
  'Dharwad': { lat: 15.4589, lng: 75.0078, zoom: 11 },
  'Ballari': { lat: 15.1394, lng: 76.9214, zoom: 11 },
  'Hassan': { lat: 13.0641, lng: 76.1030, zoom: 11 },
  'Dakshina Kannada': { lat: 12.78, lng: 75.15, zoom: 11.5 },
};

export const useMapStore = create<MapState>((set) => ({
  viewState: {
    longitude: 76.6413, // Center of Karnataka
    latitude: 15.3173,
    zoom: 6.8,
    pitch: 30,
    bearing: 0,
  },
  selectedDistrict: null,
  selectedStation: null,
  selectedCrimeId: null,
  timeOfDay: 19, // Default to evening
  layers: {
    hotspot: true,
    beatCoverage: false,
    riskScore: false,
    socioEconomic: false,
  },
  // Issue 161 §1: NO hardcoded district intelligence. This store previously
  // shipped invented counts/risk scores for nine districts; district metrics
  // now come exclusively from real backend responses via
  // `districtDataOverride` (Hotspots page builds it from
  // /dashboard/district-comparison + /ai/predictions/risk-scores).
  districtData: {},

  setViewState: (viewState) => set({ viewState }),
  setSelectedDistrict: (selectedDistrict) => set({ selectedDistrict, selectedStation: null, selectedCrimeId: null }),
  setSelectedStation: (selectedStation) => set({ selectedStation, selectedCrimeId: null }),
  setSelectedCrimeId: (selectedCrimeId) => set({ selectedCrimeId }),
  setTimeOfDay: (timeOfDay) => set({ timeOfDay }),
  
  toggleLayer: (layerKey) => set((state) => ({
    layers: {
      ...state.layers,
      [layerKey]: !state.layers[layerKey]
    }
  })),

  flyToDistrict: (districtName) => {
    const coords = DISTRICT_COORDS[districtName];
    if (coords) {
      set({
        selectedDistrict: districtName,
        viewState: {
          longitude: coords.lng,
          latitude: coords.lat,
          zoom: coords.zoom,
          pitch: 45,
          bearing: 15,
        }
      });
    }
  }
}));
