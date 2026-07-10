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
  riskScore: number;
  beatRatio: number; // percentage coverage
  topCrimeType: string;
  weeklyTrend: 'up' | 'down' | 'stable';
}

interface MapState {
  viewState: ViewState;
  selectedDistrict: string | null;
  timeOfDay: number; // 0 to 23 hours
  layers: {
    hotspot: boolean;
    beatCoverage: boolean;
    riskScore: boolean;
  };
  districtData: Record<string, DistrictInfo>;
  setViewState: (viewState: ViewState) => void;
  setSelectedDistrict: (district: string | null) => void;
  setTimeOfDay: (hour: number) => void;
  toggleLayer: (layerKey: 'hotspot' | 'beatCoverage' | 'riskScore') => void;
  flyToDistrict: (districtName: string) => void;
}

// Coordinates for Karnataka Districts
export const DISTRICT_COORDS: Record<string, { lat: number; lng: number; zoom: number }> = {
  'Bengaluru Urban': { lat: 12.9716, lng: 77.5946, zoom: 11 },
  'Mysuru': { lat: 12.2958, lng: 76.6394, zoom: 11.5 },
  'Kalaburagi': { lat: 17.3297, lng: 76.8343, zoom: 11 },
  'Belagavi': { lat: 15.8497, lng: 74.4977, zoom: 11 },
  'Tumkuru': { lat: 13.3379, lng: 77.1173, zoom: 10.5 },
  'Dharwad': { lat: 15.4589, lng: 75.0078, zoom: 11 },
  'Ballari': { lat: 15.1394, lng: 76.9214, zoom: 11 },
  'Hassan': { lat: 13.0641, lng: 76.1030, zoom: 11 },
  'Mangaluru': { lat: 12.9141, lng: 74.8560, zoom: 11.5 },
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
  timeOfDay: 19, // Default to evening
  layers: {
    hotspot: true,
    beatCoverage: false,
    riskScore: false,
  },
  districtData: {
    'Bengaluru Urban': { name: 'Bengaluru Urban', crimeCount: 1420, riskScore: 88, beatRatio: 82, topCrimeType: 'Cyber Crime & Online Fraud', weeklyTrend: 'up' },
    'Mysuru': { name: 'Mysuru', crimeCount: 450, riskScore: 54, beatRatio: 74, topCrimeType: 'Theft & Burglaries', weeklyTrend: 'down' },
    'Kalaburagi': { name: 'Kalaburagi', crimeCount: 680, riskScore: 72, beatRatio: 56, topCrimeType: 'Property Disputes', weeklyTrend: 'up' },
    'Belagavi': { name: 'Belagavi', crimeCount: 520, riskScore: 61, beatRatio: 65, topCrimeType: 'Smuggling & Excise Violations', weeklyTrend: 'stable' },
    'Tumkuru': { name: 'Tumkuru', crimeCount: 390, riskScore: 49, beatRatio: 69, topCrimeType: 'Assault', weeklyTrend: 'down' },
    'Dharwad': { name: 'Dharwad', crimeCount: 480, riskScore: 58, beatRatio: 70, topCrimeType: 'Attempted Theft', weeklyTrend: 'stable' },
    'Ballari': { name: 'Ballari', crimeCount: 610, riskScore: 69, beatRatio: 48, topCrimeType: 'Illegal Mining Violations', weeklyTrend: 'up' },
    'Hassan': { name: 'Hassan', crimeCount: 310, riskScore: 42, beatRatio: 63, topCrimeType: 'Domestic Violence', weeklyTrend: 'down' },
    'Mangaluru': { name: 'Mangaluru', crimeCount: 570, riskScore: 66, beatRatio: 78, topCrimeType: 'Narcotics Smuggling Services', weeklyTrend: 'stable' },
  },

  setViewState: (viewState) => set({ viewState }),
  setSelectedDistrict: (selectedDistrict) => set({ selectedDistrict }),
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
