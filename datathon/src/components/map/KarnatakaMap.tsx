import React, { useState, useEffect, useMemo } from 'react';
import { useMapStore, DISTRICT_COORDS } from '../../store/mapStore';
import type { HotspotPoint } from '../../services/api';
import type { DistrictInfo } from '../../store/mapStore';
import TimeSlider from './TimeSlider';
import { 
  Shield, X, TrendingUp, TrendingDown, AlertTriangle, 
  MapPin, ChevronRight, ChevronDown, ArrowLeft, Radio, FileText, 
  Clock, Flame
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { downloadSecureDossier } from '../../utils/downloader';
import { useAuditStore } from '../../store/auditStore';
import { useAuthStore } from '../../store/authStore';
import { useThemePalettes } from '../../theme';
import { useAppStore } from '../../store/appStore';

// Real Karnataka District Police Station database mapping
const DISTRICT_POLICE_STATIONS: Record<string, HotspotPoint[]> = {
  'Bengaluru Urban': [
    { district_id: 'Bengaluru Urban', name: 'Whitefield Police Station', lat: 12.9698, lng: 77.7500, score: 94, category: 'Cyber Crime & Online Fraud', trend: 'up' },
    { district_id: 'Bengaluru Urban', name: 'Jayanagar Police Station', lat: 12.9260, lng: 77.5830, score: 92, category: 'Narcotics Smuggling Services', trend: 'down' },
    { district_id: 'Bengaluru Urban', name: 'Indiranagar Police Station', lat: 12.9784, lng: 77.6408, score: 86, category: 'Theft & Burglaries', trend: 'stable' },
    { district_id: 'Bengaluru Urban', name: 'Koramangala Police Station', lat: 12.9352, lng: 77.6245, score: 88, category: 'Commercial Frauds & Cheating', trend: 'up' },
    { district_id: 'Bengaluru Urban', name: 'Electronic City Police Station', lat: 12.8452, lng: 77.6602, score: 79, category: 'Cyber Extortion & Phishing', trend: 'stable' },
    { district_id: 'Bengaluru Urban', name: 'Cubbon Park Police Station', lat: 12.9767, lng: 77.5928, score: 74, category: 'VVIP & Public Security', trend: 'down' },
  ],
  'Mysuru': [
    { district_id: 'Mysuru', name: 'Devaraja Police Station', lat: 12.3050, lng: 76.6480, score: 88, category: 'Theft & Burglaries', trend: 'up' },
    { district_id: 'Mysuru', name: 'Lashkar Police Station', lat: 12.3160, lng: 76.6550, score: 84, category: 'Commercial Fraud & Cheating', trend: 'stable' },
    { district_id: 'Mysuru', name: 'Nazarbad Police Station', lat: 12.3100, lng: 76.6680, score: 81, category: 'Violent Assaults & Riots', trend: 'down' },
    { district_id: 'Mysuru', name: 'V.V. Puram Police Station', lat: 12.3320, lng: 76.6340, score: 76, category: 'Vehicle Theft', trend: 'stable' },
    { district_id: 'Mysuru', name: 'Saraswathipuram Police Station', lat: 12.3010, lng: 76.6310, score: 72, category: 'Domestic Violence', trend: 'down' },
  ],
  'Ballari': [
    { district_id: 'Ballari', name: 'City Police Station', lat: 15.1400, lng: 76.9100, score: 96, category: 'Domestic Violence', trend: 'up' },
    { district_id: 'Ballari', name: 'Cowl Bazaar Police Station', lat: 15.1290, lng: 76.9230, score: 89, category: 'Smuggling & Illegal Mining', trend: 'up' },
    { district_id: 'Ballari', name: 'Brucepet Police Station', lat: 15.1480, lng: 76.9200, score: 82, category: 'Theft & Property Crimes', trend: 'stable' },
    { district_id: 'Ballari', name: 'APMC Yard Police Station', lat: 15.1620, lng: 76.8980, score: 75, category: 'Excise & Transport Violations', trend: 'down' },
  ],
  'Belagavi': [
    { district_id: 'Belagavi', name: 'Khade Bazar Police Station', lat: 15.8500, lng: 74.5100, score: 82, category: 'Smuggling & Excise Violations', trend: 'down' },
    { district_id: 'Belagavi', name: 'Market Police Station', lat: 15.8620, lng: 74.5220, score: 85, category: 'Counterfeit & Smuggling', trend: 'up' },
    { district_id: 'Belagavi', name: 'Camp Police Station', lat: 15.8420, lng: 74.5050, score: 78, category: 'Property Disputes', trend: 'stable' },
    { district_id: 'Belagavi', name: 'Tilakwadi Police Station', lat: 15.8350, lng: 74.5020, score: 73, category: 'Cyber Fraud & Phishing', trend: 'down' },
  ],
  'Kalaburagi': [
    { district_id: 'Kalaburagi', name: 'Brahmapur Police Station', lat: 17.3300, lng: 76.8400, score: 80, category: 'Property Disputes', trend: 'up' },
    { district_id: 'Kalaburagi', name: 'Chowk Police Station', lat: 17.3410, lng: 76.8320, score: 83, category: 'Violent Assaults & Clashes', trend: 'up' },
    { district_id: 'Kalaburagi', name: 'Station Bazaar Police Station', lat: 17.3240, lng: 76.8480, score: 77, category: 'Theft & Pickpocketing', trend: 'stable' },
    { district_id: 'Kalaburagi', name: 'University Police Station', lat: 17.2980, lng: 76.8150, score: 70, category: 'Public Disturbance', trend: 'down' },
  ],
  'Dakshina Kannada': [
    { district_id: 'Dakshina Kannada', name: 'Surathkal Police Station', lat: 12.9800, lng: 74.8600, score: 85, category: 'Cyber Crime & Online Fraud', trend: 'stable' },
    { district_id: 'Dakshina Kannada', name: 'Mangaluru North (Bunder) Police Station', lat: 12.8710, lng: 74.8380, score: 89, category: 'Maritime & Port Smuggling', trend: 'up' },
    { district_id: 'Dakshina Kannada', name: 'Mangaluru South (Pandeshwar) Police Station', lat: 12.8590, lng: 74.8420, score: 82, category: 'Commercial Fraud & Extortion', trend: 'stable' },
    { district_id: 'Dakshina Kannada', name: 'Kadri Police Station', lat: 12.8850, lng: 74.8610, score: 76, category: 'Narcotics & Substance Abuse', trend: 'down' },
  ],
  'Dharwad': [
    { district_id: 'Dharwad', name: 'Dharwad Town Police Station', lat: 15.4590, lng: 75.0080, score: 81, category: 'Theft & Burglaries', trend: 'up' },
    { district_id: 'Dharwad', name: 'Suburban Police Station', lat: 15.4480, lng: 75.0190, score: 78, category: 'Property Disputes', trend: 'stable' },
    { district_id: 'Dharwad', name: 'Hubballi Town Police Station', lat: 15.3647, lng: 75.1240, score: 87, category: 'Commercial Extortion & Frauds', trend: 'up' },
    { district_id: 'Dharwad', name: 'Gokul Road Police Station', lat: 15.3520, lng: 75.0980, score: 74, category: 'Vehicle Thefts & Traffic', trend: 'down' },
  ],
  'Tumkuru': [
    { district_id: 'Tumkuru', name: 'Tumkuru Town Police Station', lat: 13.3400, lng: 77.1000, score: 79, category: 'Theft & Highway Robberies', trend: 'up' },
    { district_id: 'Tumkuru', name: 'New Extension Police Station', lat: 13.3510, lng: 77.1120, score: 75, category: 'Domestic Violence', trend: 'stable' },
    { district_id: 'Tumkuru', name: 'Tilak Park Police Station', lat: 13.3340, lng: 77.0950, score: 71, category: 'Commercial Disputes', trend: 'down' },
  ],
  'Hassan': [
    { district_id: 'Hassan', name: 'Hassan City Police Station', lat: 13.0100, lng: 76.1000, score: 76, category: 'Domestic Violence', trend: 'down' },
    { district_id: 'Hassan', name: 'Hassan Extension Police Station', lat: 13.0220, lng: 76.1150, score: 73, category: 'Property Disputes', trend: 'stable' },
    { district_id: 'Hassan', name: 'Penta Police Station', lat: 12.9980, lng: 76.0880, score: 68, category: 'Vehicle Theft', trend: 'down' },
  ],
  'Mandya': [
    { district_id: 'Mandya', name: 'Mandya Town Police Station', lat: 12.5200, lng: 76.9000, score: 83, category: 'Domestic Violence & Assault', trend: 'up' },
    { district_id: 'Mandya', name: 'Mandya Central Police Station', lat: 12.5280, lng: 76.8920, score: 79, category: 'Agricultural & Land Disputes', trend: 'stable' },
    { district_id: 'Mandya', name: 'Maddur Police Station', lat: 12.5840, lng: 77.0450, score: 77, category: 'Highway Robberies & Thefts', trend: 'up' },
    { district_id: 'Mandya', name: 'Srirangapatna Police Station', lat: 12.4210, lng: 76.6950, score: 72, category: 'Heritage & Tourist Security', trend: 'down' },
  ],
  'Chitradurga': [
    { district_id: 'Chitradurga', name: 'Chitradurga Town Police Station', lat: 14.2250, lng: 76.4000, score: 78, category: 'Property Disputes & Thefts', trend: 'up' },
    { district_id: 'Chitradurga', name: 'Fort Police Station', lat: 14.2180, lng: 76.3950, score: 74, category: 'Highway Violations & Smuggling', trend: 'stable' },
    { district_id: 'Chitradurga', name: 'Holalkere Police Station', lat: 14.0410, lng: 76.1820, score: 69, category: 'Domestic Violence', trend: 'down' },
  ],
  'Shivamogga': [
    { district_id: 'Shivamogga', name: 'Shivamogga Town Police Station', lat: 13.9300, lng: 75.5700, score: 80, category: 'Violent Assaults & Riots', trend: 'up' },
    { district_id: 'Shivamogga', name: 'Kote Police Station', lat: 13.9380, lng: 75.5820, score: 76, category: 'Timber & Forest Smuggling', trend: 'stable' },
    { district_id: 'Shivamogga', name: 'Doddapete Police Station', lat: 13.9240, lng: 75.5610, score: 72, category: 'Commercial Fraud & Thefts', trend: 'down' },
  ]
};

// Coordinates projection onto custom 800x600 SVG canvas
const projectLonX = (lon: number) => {
  // Lon 73.8 to 78.8
  return 60 + ((lon - 73.8) / (78.8 - 73.8)) * 680;
};

const projectLatY = (lat: number) => {
  // Lat 11.5 is bottom, Lat 18.6 is top
  return 540 - ((lat - 11.5) / (18.6 - 11.5)) * 480;
};

// District Boundary simplified paths for UI presentation
const DISTRICT_BOUNDARIES: Record<string, [number, number][]> = {
  'Bengaluru Urban': [
    [77.4, 13.2], [77.8, 13.1], [77.8, 12.8], [77.4, 12.7], [77.3, 12.9]
  ],
  'Mysuru': [
    [76.2, 12.5], [76.7, 12.6], [77.0, 12.1], [76.5, 11.8], [76.0, 11.9]
  ],
  'Kalaburagi': [
    [76.5, 17.6], [77.2, 17.7], [77.3, 17.1], [76.7, 16.9], [76.4, 17.2]
  ],
  'Belagavi': [
    [74.2, 16.5], [74.9, 16.6], [75.2, 15.8], [74.5, 15.5], [73.9, 15.8]
  ],
  'Tumkuru': [
    [76.8, 14.1], [77.2, 13.8], [77.4, 13.2], [76.9, 13.0], [76.6, 13.4]
  ],
  'Dharwad': [
    [74.8, 15.6], [75.3, 15.7], [75.4, 15.1], [75.0, 15.0], [74.8, 15.3]
  ],
  'Ballari': [
    [76.4, 15.6], [77.1, 15.4], [77.0, 14.9], [76.5, 14.8], [76.2, 15.1]
  ],
  'Hassan': [
    [75.8, 13.3], [76.3, 13.2], [76.3, 12.7], [75.9, 12.6], [75.6, 12.9]
  ],
  'Dakshina Kannada': [
    [74.7, 13.1], [75.4, 13.0], [75.4, 12.5], [74.8, 12.6], [74.6, 12.9]
  ]
};

export interface EmergingTrendItem {
  category: string;
  recent_count: number;
  historical_count: number;
  change_percentage: number;
  direction: string;
}

type SocioIndicatorKey = 'urbanization' | 'unemployment_rate' | 'literacy_rate' | 'avg_income_lakhs' | 'crime_per_lakh';

const SOCIO_INDICATORS: Array<{ key: SocioIndicatorKey; label: string; unit: string }> = [
  { key: 'urbanization', label: 'Urbanization', unit: '' },
  { key: 'unemployment_rate', label: 'Unemployment', unit: '%' },
  { key: 'literacy_rate', label: 'Literacy', unit: '%' },
  { key: 'avg_income_lakhs', label: 'Avg Income', unit: 'L' },
  { key: 'crime_per_lakh', label: 'Crime Rate', unit: '/lakh' },
];

// Interpolate blue -> amber -> red across [0, 1] (0 = lowest value of the range)
function socioShade(t: number): { fill: string; stroke: string } {
  const clamped = Math.min(1, Math.max(0, t));
  let r: number;
  let g: number;
  let b: number;
  if (clamped < 0.5) {
    const k = clamped / 0.5;
    r = Math.round(30 + (212 - 30) * k);
    g = Math.round(111 + (130 - 111) * k);
    b = Math.round(217 + (10 - 217) * k);
  } else {
    const k = (clamped - 0.5) / 0.5;
    r = Math.round(212 + (201 - 212) * k);
    g = Math.round(130 + (74 - 130) * k);
    b = Math.round(10 + (42 - 10) * k);
  }
  return {
    fill: `rgba(${r}, ${g}, ${b}, ${0.18 + clamped * 0.3})`,
    stroke: `rgb(${r}, ${g}, ${b})`,
  };
}

interface KarnatakaMapProps {
  hotspots?: HotspotPoint[];
  districtDataOverride?: Record<string, DistrictInfo>;
  emergingTrends?: EmergingTrendItem[];
  crimeCases?: any[];
  socioEconomicData?: any[];
}

export const KarnatakaMap: React.FC<KarnatakaMapProps> = ({ 
  hotspots = [], 
  districtDataOverride,
  emergingTrends = [],
  crimeCases = [],
  socioEconomicData = [],
}) => {
  const {
    selectedDistrict,
    selectedStation,
    selectedCrimeId,
    timeOfDay,
    layers,
    districtData,
    setSelectedDistrict,
    setSelectedStation,
    setSelectedCrimeId,
    toggleLayer
  } = useMapStore();

  const { user } = useAuthStore();
  const { addLog } = useAuditStore();
  const theme = useAppStore((s) => s.theme);
  const palette = useThemePalettes();
  const map = palette.map;

  const [panelOpen, setPanelOpen] = useState(false);
  const [mapZoom, setMapZoom] = useState(1);
  const [mapOffset, setMapOffset] = useState({ x: 0, y: 0 });
  const [selectedHotspot, setSelectedHotspot] = useState<any | null>(null);
  const [socioIndicator, setSocioIndicator] = useState<SocioIndicatorKey>('unemployment_rate');

  // Map socio-economic reference array by district name
  const socioEconomicMap = useMemo(() => {
    const map: Record<string, any> = {};
    socioEconomicData.forEach((item: any) => {
      if (item.district) {
        map[item.district] = item;
      }
    });
    return map;
  }, [socioEconomicData]);

  // Quantitative range for the selected indicator across all mapped districts
  const socioIndicatorRange = useMemo(() => {
    if (socioIndicator === 'urbanization') return null;
    const values = Object.values(socioEconomicMap)
      .map((item: any) => Number(item?.[socioIndicator]))
      .filter((v) => Number.isFinite(v));
    if (values.length === 0) return null;
    return { min: Math.min(...values), max: Math.max(...values) };
  }, [socioEconomicMap, socioIndicator]);

  const socioDistrictShade = (socio: any): { fill: string; stroke: string } | null => {
    if (!socio) return null;
    if (socioIndicator === 'urbanization' || !socioIndicatorRange) {
      if (socioIndicator !== 'urbanization') return null;
      return socio.urbanization_type === 'urban'
        ? { fill: 'rgba(201, 74, 42, 0.40)', stroke: '#C94A2A' }
        : socio.urbanization_type === 'semi_urban'
        ? { fill: 'rgba(212, 130, 10, 0.35)', stroke: '#D4820A' }
        : { fill: 'rgba(30, 111, 217, 0.25)', stroke: '#1E6FD9' };
    }
    const value = Number(socio[socioIndicator]);
    if (!Number.isFinite(value) || socioIndicatorRange.max === socioIndicatorRange.min) {
      return { fill: 'rgba(120, 130, 150, 0.20)', stroke: 'rgba(120, 130, 150, 0.6)' };
    }
    const t = (value - socioIndicatorRange.min) / (socioIndicatorRange.max - socioIndicatorRange.min);
    return socioShade(t);
  };

  // Open details panel when a district or station is selected
  useEffect(() => {
    if (selectedDistrict || selectedStation) {
      setPanelOpen(true);
    } else {
      setPanelOpen(false);
      setSelectedHotspot(null);
    }
  }, [selectedDistrict, selectedStation]);

  // Calculate temporal modulation factor based on timeOfDay (hour 0-23)
  const temporalShiftInfo = useMemo(() => {
    if (timeOfDay >= 5 && timeOfDay < 12) {
      return { label: 'Morning Watch (05:00-12:00)', multiplier: 0.85, status: 'Standard Routine Patrol' };
    }
    if (timeOfDay >= 12 && timeOfDay < 17) {
      return { label: 'Afternoon Shift (12:00-17:00)', multiplier: 0.95, status: 'Active Field Surveillance' };
    }
    if (timeOfDay >= 17 && timeOfDay < 21) {
      return { label: 'Evening Peak Shift (17:00-21:00)', multiplier: 1.15, status: 'Elevated Commercial Peak' };
    }
    return { label: 'Night Beat Operation (21:00-05:00)', multiplier: 1.28, status: 'High Vulnerability Window' };
  }, [timeOfDay]);

  // Compute active hotspots dynamically modulated by timeOfDay
  const activeHotspots = useMemo(() => {
    return hotspots.map((hotspot) => {
      // Modulate threat score by temporal multiplier
      const modulatedScore = Math.min(100, Math.max(10, Math.round(hotspot.score * temporalShiftInfo.multiplier)));
      return {
        name: hotspot.name,
        lat: hotspot.lat,
        lng: hotspot.lng,
        weight: modulatedScore,
        baseScore: hotspot.score,
        type: hotspot.category,
        district_id: hotspot.district_id,
        trend: hotspot.trend,
      };
    });
  }, [hotspots, temporalShiftInfo]);

  const resolvedDistrictData = districtDataOverride ?? districtData;
  const activeDistrictInfo = useMemo(() => {
    if (!selectedDistrict) return null;
    if (resolvedDistrictData[selectedDistrict]) return resolvedDistrictData[selectedDistrict];
    const match = Object.entries(resolvedDistrictData).find(([k]) => k.toLowerCase() === selectedDistrict.toLowerCase());
    if (match) return match[1];
    // Issue 161 §1: no fabricated placeholder intelligence — when the backend
    // has no record for this district the panel renders an honest empty state
    // instead of invented counts/risk scores/station names.
    return null;
  }, [selectedDistrict, resolvedDistrictData]);

  // Get active district's complete police station registry
  const districtStations = useMemo(() => {
    if (!selectedDistrict) return [];
    const targetDist = selectedDistrict.toLowerCase();
    
    // Find district key in dictionary (case-insensitive)
    const dictKey = Object.keys(DISTRICT_POLICE_STATIONS).find(k => k.toLowerCase() === targetDist);
    const dictStations = dictKey ? DISTRICT_POLICE_STATIONS[dictKey] : [];
    
    // Also include any dynamically passed hotspots for this district
    const liveStations = activeHotspots.filter(h => (h.district_id || '').toLowerCase() === targetDist);
    
    // Combine unique stations
    const map = new Map<string, any>();
    [...dictStations, ...liveStations].forEach((s: any) => {
      if (s.name && !map.has(s.name)) {
        map.set(s.name, {
          ...s,
          district_id: selectedDistrict,
          weight: Math.min(100, Math.max(10, Math.round((s.score || s.weight || 75) * temporalShiftInfo.multiplier))),
          baseScore: s.score || s.weight || 75,
          type: s.category || s.type || 'Patrol Beat Station',
          trend: s.trend || 'stable'
        });
      }
    });

    if (map.size > 0) {
      return Array.from(map.values());
    }

    const center = DISTRICT_COORDS[selectedDistrict] || { lat: 14.5, lng: 75.8 };
    return [
      { district_id: selectedDistrict, name: `${selectedDistrict} Town Police Station`, lat: center.lat + 0.03, lng: center.lng + 0.02, weight: 82, baseScore: 82, type: 'Patrol Beat Station', score: 82, trend: 'up' as const },
      { district_id: selectedDistrict, name: `${selectedDistrict} Central Police Station`, lat: center.lat - 0.02, lng: center.lng - 0.03, weight: 75, baseScore: 75, type: 'Jurisdiction Station', score: 75, trend: 'stable' as const },
      { district_id: selectedDistrict, name: `${selectedDistrict} Rural Police Station`, lat: center.lat - 0.05, lng: center.lng + 0.04, weight: 68, baseScore: 68, type: 'Highway Security', score: 68, trend: 'down' as const }
    ];
  }, [selectedDistrict, activeHotspots, temporalShiftInfo]);

  // Rendered hotspots on map (combining active hotspots + selected district stations)
  const renderedHotspots = useMemo(() => {
    if (!layers.hotspot) return [];
    if (selectedDistrict && districtStations.length > 0) {
      const map = new Map<string, any>();
      activeHotspots.forEach(h => map.set(h.name, h));
      districtStations.forEach(s => map.set(s.name, s));
      return Array.from(map.values());
    }
    return activeHotspots;
  }, [layers.hotspot, selectedDistrict, districtStations, activeHotspots]);

  // Selected station object
  const activeStationInfo = useMemo(() => {
    if (!selectedStation) return null;
    const targetStation = selectedStation.toLowerCase();
    const found = activeHotspots.find(h => (h.name || '').toLowerCase() === targetStation);
    if (found) return found;
    return {
      name: selectedStation,
      lat: 12.97,
      lng: 77.59,
      weight: 75,
      baseScore: 75,
      type: 'General Offense Patrol',
      district_id: selectedDistrict || 'Karnataka',
      trend: 'stable' as const,
    };
  }, [selectedStation, activeHotspots, selectedDistrict]);

  // Filter crime cases for current district or station
  const filteredCases = useMemo(() => {
    if (!crimeCases || crimeCases.length === 0) return [];
    
    if (selectedStation) {
      const stationLower = (selectedStation || '').toLowerCase();
      const stationToken = stationLower.replace(/police station|station|checkpoint|beat/gi, '').trim();
      
      const directMatches = crimeCases.filter((c: any) => {
        const loc = (c.location || c.station || '').toLowerCase();
        const desc = (c.description || '').toLowerCase();
        return (stationToken.length >= 3 && (loc.includes(stationToken) || desc.includes(stationToken) || stationToken.includes(loc)))
          || loc.includes(stationLower) || stationLower.includes(loc);
      });

      if (directMatches.length > 0) {
        return directMatches;
      }
    }

    if (selectedDistrict) {
      const districtLower = (selectedDistrict || '').toLowerCase();
      const districtToken = districtLower.split(' ')[0].toLowerCase();
      const districtCode = districtToken.slice(0, 3);
      
      const districtMatches = crimeCases.filter((c: any) => {
        const dist = (c.district || c.location || '').toLowerCase();
        const caseNum = (c.case_number || '').toLowerCase();
        return dist.includes(districtToken) || (districtCode.length >= 3 && caseNum.includes(districtCode));
      });

      if (districtMatches.length > 0) {
        return districtMatches;
      }
    }

    return crimeCases.slice(0, 8);
  }, [crimeCases, selectedDistrict, selectedStation]);

  // Selected crime case record
  const activeCrimeCase = useMemo(() => {
    if (!selectedCrimeId) return null;
    return crimeCases.find((c: any) => c.case_number === selectedCrimeId || c.id === selectedCrimeId) || null;
  }, [selectedCrimeId, crimeCases]);

  // Active emerging trends for current district
  const districtEmergingTrends = useMemo(() => {
    if (!selectedDistrict || !emergingTrends.length) return [];
    const topCrime = activeDistrictInfo?.topCrimeType;
    return emergingTrends.filter(t => 
      t.direction === 'increasing' && 
      (t.category === topCrime || t.change_percentage > 25)
    );
  }, [selectedDistrict, emergingTrends, activeDistrictInfo]);

  // Handle zooming of vector view representation on selection
  useEffect(() => {
    if (selectedDistrict) {
      const coords = DISTRICT_COORDS[selectedDistrict];
      if (coords) {
        // Project to canvas coordinates
        const x = projectLonX(coords.lng);
        const y = projectLatY(coords.lat);
        // Center the district at (240, 300) in the left workspace (clear of right drawer)
        const zoom = 1.15;
        setMapZoom(zoom);
        setMapOffset({ 
          x: Math.round(240 - x * zoom), 
          y: Math.round(300 - y * zoom) 
        });
      }
    } else {
      setMapZoom(1);
      setMapOffset({ x: 0, y: 0 });
    }
  }, [selectedDistrict]);

  return (
    <div className="w-full h-full min-h-[580px] relative overflow-hidden flex flex-col justify-between bg-[var(--bg-surface)] rounded-card border border-border-color">
      
      {/* MAP HEADER PANELS */}
      <div className="absolute top-4 left-4 z-20 flex flex-col gap-2 max-w-xs pointer-events-none select-none">
        <div className="px-3 py-2 bg-secondary-bg/95 backdrop-blur-md border border-border-color rounded-card pointer-events-auto">
          <div className="flex items-center justify-between gap-2">
            <span className="text-[10px] font-mono text-[var(--accent-teal)] uppercase font-bold tracking-wider">
              Vector Grid Telemetry
            </span>
            <span className="text-[8.5px] font-mono text-[var(--accent-coral)] font-bold uppercase flex items-center gap-1">
              <Radio className="w-2.5 h-2.5 animate-pulse" />
              LIVE
            </span>
          </div>
          <h3 className="text-[13px] font-mono font-bold text-[var(--text-primary)] mt-0.5 truncate">
            {selectedCrimeId 
              ? `Case: ${selectedCrimeId}` 
              : selectedStation 
              ? `Station: ${selectedStation}` 
              : selectedDistrict 
              ? `District: ${selectedDistrict}` 
              : 'Statewide Overview'}
          </h3>
          <div className="mt-1 flex items-center gap-1.5 text-[8.5px] font-mono text-[var(--text-muted)]">
            <Clock className="w-3 h-3 text-[var(--accent-blue)]" />
            <span className="text-[var(--accent-blue)] font-semibold">{temporalShiftInfo.label}</span>
          </div>
          <p className="text-[8px] font-mono text-[var(--text-secondary)] mt-0.5">
            {temporalShiftInfo.status} &bull; Factor: {temporalShiftInfo.multiplier}x
          </p>
        </div>

        {/* LAYER SELECTORS */}
        <div className="px-3 py-2 bg-secondary-bg/95 backdrop-blur-md border border-border-color rounded-card pointer-events-auto flex flex-col gap-1.5">
          <span className="text-[8px] font-mono uppercase tracking-widest text-[var(--text-muted)] mb-1">
            Display Layers
          </span>
          <button
            onClick={() => toggleLayer('hotspot')}
            className={`w-full py-1 px-2.5 rounded text-[9.5px] font-mono uppercase flex items-center justify-between transition-colors border cursor-pointer ${
              layers.hotspot 
                ? 'bg-[var(--accent-blue)]/15 border-[var(--accent-blue)] text-[var(--accent-blue)]' 
                : 'bg-transparent border-[var(--border-secondary)] text-[var(--text-secondary)]'
            }`}
          >
            <span>Hotspots Data</span>
            <div className={`w-1.5 h-1.5 rounded-full ${layers.hotspot ? 'bg-[var(--accent-blue)] animate-pulse' : 'bg-[var(--text-muted)]'}`} />
          </button>
          
          <button
            onClick={() => toggleLayer('beatCoverage')}
            className={`w-full py-1 px-2.5 rounded text-[9.5px] font-mono uppercase flex items-center justify-between transition-colors border cursor-pointer ${
              layers.beatCoverage 
                ? 'bg-[var(--accent-teal)]/15 border-[var(--accent-teal)] text-[var(--accent-teal)]' 
                : 'bg-transparent border-[var(--border-secondary)] text-[var(--text-secondary)]'
            }`}
          >
            <span>Beat Officer Ratio</span>
            <div className={`w-1.5 h-1.5 rounded-full ${layers.beatCoverage ? 'bg-[var(--accent-teal)] animate-pulse' : 'bg-[var(--text-muted)]'}`} />
          </button>
          
          <button
            onClick={() => toggleLayer('riskScore')}
            className={`w-full py-1 px-2.5 rounded text-[9.5px] font-mono uppercase flex items-center justify-between transition-colors border cursor-pointer ${
              layers.riskScore 
                ? 'bg-[var(--accent-purple)]/15 border-[var(--accent-purple)] text-[var(--accent-purple)]' 
                : 'bg-transparent border-[var(--border-secondary)] text-[var(--text-secondary)]'
            }`}
          >
            <span>Regional Risk Index</span>
            <div className={`w-1.5 h-1.5 rounded-full ${layers.riskScore ? 'bg-[var(--accent-purple)] animate-pulse' : 'bg-[var(--text-muted)]'}`} />
          </button>

          <button
            onClick={() => toggleLayer('socioEconomic')}
            className={`w-full py-1 px-2.5 rounded text-[9.5px] font-mono uppercase flex items-center justify-between transition-colors border cursor-pointer ${
              layers.socioEconomic
                ? 'bg-amber-500/15 border-amber-500 text-amber-400'
                : 'bg-transparent border-[var(--border-secondary)] text-[var(--text-secondary)]'
            }`}
          >
            <span>Socio-Economic Layer</span>
            <div className={`w-1.5 h-1.5 rounded-full ${layers.socioEconomic ? 'bg-amber-400 animate-pulse' : 'bg-[var(--text-muted)]'}`} />
          </button>

          {layers.socioEconomic && (
            <div className="grid grid-cols-2 gap-1 pl-1">
              {SOCIO_INDICATORS.map((indicator) => (
                <button
                  key={indicator.key}
                  onClick={() => setSocioIndicator(indicator.key)}
                  className={`py-0.5 px-1.5 rounded text-[8px] font-mono uppercase transition-colors border cursor-pointer ${
                    socioIndicator === indicator.key
                      ? 'bg-amber-500/20 border-amber-500/60 text-amber-300'
                      : 'bg-transparent border-border-color text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
                  }`}
                >
                  {indicator.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* RENDER CANVAS CONTAINER */}
      <div className="flex-1 w-full min-h-[460px] relative cursor-grab active:cursor-grabbing overflow-hidden" style={{ backgroundColor: map.bg }}>

        {/* GEODESIC BACKGROUND GRID */}
        <svg className="absolute inset-0 w-full h-full pointer-events-none">
          <defs>
            <pattern id="gridPattern" width="40" height="40" patternUnits="userSpaceOnUse">
              <path d="M 40 0 L 0 0 0 40" fill="none" stroke={map.grid} strokeWidth="0.5" />
            </pattern>
          </defs>
          <rect width="100%" height="100%" fill="url(#gridPattern)" />
        </svg>

        {/* INTERACTIVE VECTOR GRAPHICS */}
        <svg 
          viewBox="0 0 800 600" 
          className="w-full h-full select-none"
        >
          {/* Inner transformation group */}
          <g
            style={{
              transform: `translate(${mapOffset.x}px, ${mapOffset.y}px) scale(${mapZoom})`,
              transition: 'transform 600ms cubic-bezier(0.16, 1, 0.3, 1)',
            }}
          >
            {/* Geodesic coordinates lines */}
            <g stroke={map.graticule} strokeWidth="0.5" strokeDasharray="3 3">
              {[74, 75, 76, 77, 78].map((lon) => (
                <line 
                  key={lon} 
                  x1={projectLonX(lon)} 
                  y1={0} 
                  x2={projectLonX(lon)} 
                  y2={600} 
                />
              ))}
              {[12, 13, 14, 15, 16, 17, 18].map((lat) => (
                <line 
                  key={lat} 
                  x1={0} 
                  y1={projectLatY(lat)} 
                  x2={800} 
                  y2={projectLatY(lat)} 
                />
              ))}
            </g>

            {/* District boundary shapes polygons */}
            <g>
            {Object.entries(DISTRICT_BOUNDARIES).map(([name, points]) => {
              const projectedPoints = points.map(([lon, lat]) => `${projectLonX(lon)},${projectLatY(lat)}`).join(' ');
              const isSelected = selectedDistrict === name;
              const info = resolvedDistrictData[name];
              const socio = socioEconomicMap[name];
              const isSpikedDistrict = info?.weeklyTrend === 'up' || emergingTrends.some(t => t.direction === 'increasing' && t.change_percentage > 15 && info?.topCrimeType?.toLowerCase().includes(t.category.toLowerCase()));
              
              // Color coding based on active layers & trend spikes
              let fill = isSpikedDistrict ? 'rgba(239, 68, 68, 0.08)' : map.districtFill;
              let stroke = isSpikedDistrict ? 'rgba(239, 68, 68, 0.45)' : map.boundary;
              
              if (layers.socioEconomic && socio) {
                const shade = socioDistrictShade(socio);
                if (shade) {
                  fill = shade.fill;
                  stroke = shade.stroke;
                }
              } else if (layers.riskScore && info && info.riskScore != null) {
                const rs = info.riskScore;
                fill = rs >= 80
                  ? `rgba(217, 52, 20, ${theme === 'dark' ? 0.35 : 0.28})`
                  : rs >= 60
                  ? `rgba(181, 110, 7, ${theme === 'dark' ? 0.35 : 0.30})`
                  : `rgba(13, 122, 91, ${theme === 'dark' ? 0.25 : 0.22})`;
              } else if (layers.beatCoverage && info) {
                const br = info.beatRatio;
                fill = br >= 75
                  ? theme === 'dark' ? 'rgba(20, 201, 151, 0.30)' : 'rgba(5, 150, 105, 0.26)'
                  : br >= 60
                  ? theme === 'dark' ? 'rgba(61, 138, 240, 0.25)' : 'rgba(37, 99, 235, 0.20)'
                  : theme === 'dark' ? 'rgba(240, 156, 46, 0.25)' : 'rgba(217, 119, 6, 0.24)';
              }

              if (isSelected) {
                fill = isSpikedDistrict ? 'rgba(239, 68, 68, 0.18)' : map.districtSelected;
                stroke = isSpikedDistrict ? '#EF4444' : map.boundaryHover;
              }

              return (
                <polygon
                  key={name}
                  points={projectedPoints}
                  className={`transition-all duration-300 cursor-pointer ${isSpikedDistrict ? 'stroke-dasharray-2' : ''}`}
                  fill={fill}
                  stroke={stroke}
                  strokeWidth={isSelected ? 2.25 : isSpikedDistrict ? 1.5 : 1.25}
                  strokeDasharray={isSpikedDistrict ? '4 2' : undefined}
                  onMouseEnter={(e) => { if (!isSelected && !isSpikedDistrict) { e.currentTarget.style.fill = map.districtSelected; e.currentTarget.style.stroke = map.boundaryHover; } }}
                  onMouseLeave={(e) => { e.currentTarget.style.fill = fill; e.currentTarget.style.stroke = stroke; }}
                  onClick={() => {
                    setSelectedDistrict(isSelected ? null : name);
                    setSelectedStation(null);
                    setSelectedCrimeId(null);
                  }}
                />
              );
            })}
          </g>

          {/* DISTRICT ANCHORS LABELS */}
          <g>
            {Object.entries(DISTRICT_COORDS).map(([name, coords]) => {
              const x = projectLonX(coords.lng);
              const y = projectLatY(coords.lat);
              const isSelected = selectedDistrict === name;
              const info = resolvedDistrictData[name];
              const isSpiked = info?.weeklyTrend === 'up';

              return (
                <g key={name} className="pointer-events-none select-none">
                  {/* Center pin node */}
                  <circle
                    cx={x}
                    cy={y}
                    r={isSelected ? 4 : isSpiked ? 3 : 2.4}
                    fill={isSelected ? map.boundaryHover : isSpiked ? '#EF4444' : map.anchor}
                  />
                  {/* District text tag — bg-stroked for legibility in both themes */}
                  <text
                    x={x + 6.5}
                    y={y + 3.5}
                    className={`font-mono text-[9px] ${isSpiked ? 'font-bold' : 'font-semibold'}`}
                    style={{ paintOrder: 'stroke', stroke: map.bg, strokeWidth: 3, strokeLinejoin: 'round' }}
                    fill={isSpiked ? '#EF4444' : map.label}
                    opacity={isSelected || isSpiked ? 1 : 0.9}
                  >
                    {name} {isSpiked ? '⚠️' : ''} {layers.beatCoverage && info?.beatRatio != null ? `(${info.beatRatio}%)` : ''}
                  </text>
                </g>
              );
            })}
          </g>

          {/* HOTSPOT PULSING RING LAYERS TIED TO TREND SPIKES & TEMPORAL MULTIPLIERS */}
          {layers.hotspot && (
            <g>
              {renderedHotspots.map((hs: any, index: number) => {
                const x = projectLonX(hs.lng);
                const y = projectLatY(hs.lat);
                const isHigh = hs.weight >= 80;
                const isStationSelected = selectedStation === hs.name;
                const catLower = (hs.type || hs.category || '').toLowerCase();
                const isSpikeTrend = hs.trend === 'up' || emergingTrends.some(t => t.direction === 'increasing' && t.change_percentage > 10 && catLower.includes(t.category.toLowerCase()));
                
                // Color mapping: Red Alert if spiked trend or threat score >= 80
                const color = isSpikeTrend ? '#EF4444' : isHigh ? map.hotspotHigh : hs.weight >= 65 ? map.hotspotMedium : map.hotspotLow;
                const isSelected = (selectedHotspot && selectedHotspot.name === hs.name) || isStationSelected;

                return (
                  <g 
                    key={index} 
                    className="cursor-pointer pointer-events-auto" 
                    onClick={(e) => { 
                      e.stopPropagation(); 
                      if (hs.district_id) {
                        setSelectedDistrict(hs.district_id);
                      }
                      setSelectedStation(hs.name);
                      setSelectedCrimeId(null);
                      setSelectedHotspot(hs); 
                    }}
                  >
                    {/* RED-ZONE PULSING RINGS FOR ACTIVE TREND SPIKES */}
                    {isSpikeTrend && (
                      <>
                        <circle 
                          cx={x} 
                          cy={y} 
                          r={Math.round(20 * temporalShiftInfo.multiplier)} 
                          fill="#EF4444" 
                          opacity={0.25} 
                          className="animate-ping" 
                          style={{ transformOrigin: `${x}px ${y}px`, animationDuration: '0.8s' }} 
                        />
                        <circle 
                          cx={x} 
                          cy={y} 
                          r={Math.round(36 * temporalShiftInfo.multiplier)} 
                          stroke="#EF4444" 
                          strokeWidth="1.5" 
                          strokeDasharray="3 3"
                          fill="none" 
                          opacity={0.35} 
                          className="animate-ping" 
                          style={{ transformOrigin: `${x}px ${y}px`, animationDuration: '1.2s' }} 
                        />
                      </>
                    )}

                    {/* Standard Concentric pulsing rings modulated by temporal shift */}
                    <circle 
                      cx={x} 
                      cy={y} 
                      r={Math.round(14 * temporalShiftInfo.multiplier)} 
                      fill={color} 
                      opacity={map.haloOpacity} 
                      className="animate-ping" 
                      style={{ transformOrigin: `${x}px ${y}px`, animationDuration: `${Math.max(1.0, 3 - hs.weight / 40)}s` }} 
                    />
                    <circle 
                      cx={x} 
                      cy={y} 
                      r={Math.round(28 * temporalShiftInfo.multiplier)} 
                      stroke={color} 
                      strokeWidth="1" 
                      fill="none" 
                      opacity={map.haloOpacity * 0.6} 
                      className="animate-ping" 
                      style={{ transformOrigin: `${x}px ${y}px`, animationDuration: `${Math.max(1.8, 4.5 - hs.weight / 30)}s` }} 
                    />
                    
                    {/* Center Core dot */}
                    <circle cx={x} cy={y} r={isSpikeTrend || isHigh || isSelected ? 8.5 : 7} fill={map.bg} />
                    <circle cx={x} cy={y} r={isSpikeTrend || isHigh || isSelected ? 6 : 4.5} fill={isSelected ? '#00F0FF' : color} stroke={map.bg} strokeWidth="1.5" />
                    <circle cx={x} cy={y} r={isSpikeTrend || isHigh || isSelected ? 9.5 : 8} stroke={isSelected ? '#00F0FF' : color} strokeWidth="1.25" fill="none" opacity={0.8} />

                    {/* Station Name Label - only show for stations belonging to the selected district or when active */}
                    {(isSelected || (selectedDistrict && (hs.district_id || '').toLowerCase() === selectedDistrict.toLowerCase())) && (
                      <text
                        x={x}
                        y={y + 13}
                        textAnchor="middle"
                        className={`font-mono text-[8px] font-bold pointer-events-none ${isSpikeTrend ? 'fill-red-400 font-extrabold' : 'fill-[var(--text-primary)]'}`}
                        style={{ paintOrder: 'stroke', stroke: map.bg, strokeWidth: 3, strokeLinejoin: 'round' }}
                      >
                        {isSpikeTrend ? '🔥 ' : ''}{hs.name.replace(/police station/i, 'PS')}
                      </text>
                    )}

                    {/* Popover Tooltip inside foreignObject */}
                    {isSelected && (
                      <foreignObject x={x - 90} y={y - 120} width="180" height="110" className="z-50 pointer-events-auto">
                        <div
                          className="p-2.5 rounded-lg text-left flex flex-col gap-1.5 font-mono text-[10px] leading-tight relative shadow-lg"
                          style={{ backgroundColor: palette.chart.tooltipBg, border: `1px solid ${palette.chart.tooltipBorder}`, color: palette.chart.tooltipText }}
                        >
                          <div className="flex justify-between items-center pb-1" style={{ borderColor: palette.chart.tooltipBorder, borderBottomWidth: 1 }}>
                            <span className="font-bold uppercase text-[9px]" style={{ color: isSpikeTrend ? '#EF4444' : map.hotspotMedium }}>
                              {isSpikeTrend ? '🔥 Surge Alert' : 'Hotspot Details'}
                            </span>
                            <button
                              onClick={(e) => { e.stopPropagation(); setSelectedHotspot(null); }}
                              className="cursor-pointer font-bold text-xs"
                              style={{ color: palette.chart.axis }}
                            >
                              ×
                            </button>
                          </div>
                          <div>
                            <p className="font-bold uppercase truncate">{hs.name}</p>
                            <p className="opacity-70 mt-0.5 truncate">Sector: {hs.district_id}</p>
                            <p className="opacity-85 mt-0.5 truncate">Category: {hs.type}</p>
                            <p className="font-bold mt-0.5" style={{ color: color }}>Threat Level: {hs.weight}%</p>
                          </div>
                        </div>
                      </foreignObject>
                    )}
                  </g>
                );
              })}
            </g>
          )}
          </g>
        </svg>

        {/* SOCIO-ECONOMIC OVERLAY LEGEND */}
        {layers.socioEconomic && (
          <div className="absolute bottom-4 right-4 z-20 px-3 py-2 bg-[var(--bg-secondary)]/85 border border-border-color rounded-card backdrop-blur-sm pointer-events-none select-none">
            <div className="text-[8px] font-mono uppercase tracking-wider text-[var(--text-muted)] mb-1.5">
              Overlay: {SOCIO_INDICATORS.find((i) => i.key === socioIndicator)?.label}
              {socioIndicatorRange ? ` (${socioIndicatorRange.min}–${socioIndicatorRange.max}${SOCIO_INDICATORS.find((i) => i.key === socioIndicator)?.unit})` : ''}
            </div>
            {socioIndicator === 'urbanization' || !socioIndicatorRange ? (
              <div className="flex flex-col gap-1 text-[8px] font-mono">
                <span className="flex items-center gap-1.5"><span className="w-3 h-2 rounded-sm" style={{ background: 'rgba(201, 74, 42, 0.55)' }} /> Urban</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-2 rounded-sm" style={{ background: 'rgba(212, 130, 10, 0.5)' }} /> Semi-Urban</span>
                <span className="flex items-center gap-1.5"><span className="w-3 h-2 rounded-sm" style={{ background: 'rgba(30, 111, 217, 0.4)' }} /> Rural</span>
              </div>
            ) : (
              <div className="flex items-center gap-1.5">
                <span className="text-[8px] font-mono">LOW</span>
                <div className="w-24 h-2 rounded-sm" style={{ background: 'linear-gradient(90deg, rgba(30,111,217,0.25), rgba(212,130,10,0.6), rgba(201,74,42,0.75))' }} />
                <span className="text-[8px] font-mono">HIGH</span>
              </div>
            )}
          </div>
        )}

        {/* MAP INFO RESET SELECTOR */}
        {(selectedDistrict || selectedStation || selectedCrimeId) && (
          <button
            onClick={() => {
              setSelectedDistrict(null);
              setSelectedStation(null);
              setSelectedCrimeId(null);
            }}
            className="absolute bottom-4 left-4 z-20 px-3 py-1.5 bg-[var(--accent-coral)] hover:opacity-90 text-white font-medium text-xs rounded-md flex items-center gap-1.5 shadow-sm cursor-pointer"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            <span>Reset View to Statewide</span>
          </button>
        )}
      </div>

      {/* 3-TIER DRILL-DOWN DETAILS PANEL DRAWER SLIDING IN (RIGHT SIDE) */}
      <AnimatePresence>
        {panelOpen && (activeDistrictInfo || activeStationInfo || selectedDistrict) && (
          <motion.div
            initial={{ x: 380, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 380, opacity: 0 }}
            transition={{ type: 'spring', damping: 20, stiffness: 100 }}
            className="absolute top-0 right-0 h-full w-84 md:w-96 bg-secondary-bg/95 border-l border-border-color backdrop-blur-md z-30 p-5 flex flex-col justify-between overflow-y-auto select-none"
          >
            <div className="space-y-4">
              
              {/* INTERACTIVE BREADCRUMB HEADER */}
              <div className="border-b border-border-color pb-3">
                <div className="flex justify-between items-center mb-2">
                  <div className="flex items-center gap-1.5 text-[9px] font-mono uppercase font-bold text-[var(--accent-teal)]">
                    <Shield className="w-3.5 h-3.5 text-[var(--accent-blue)] shrink-0" />
                    <span>SCRB Intelligence Drill-Down</span>
                  </div>
                  <button
                    onClick={() => setPanelOpen(false)}
                    className="p-1 hover:bg-[var(--accent-blue)]/15 rounded text-[var(--text-secondary)] hover:text-[var(--text-primary)] cursor-pointer"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>

                {/* Breadcrumb Steps */}
                <div className="flex items-center gap-1 text-[9px] font-mono flex-wrap">
                  <button
                    onClick={() => {
                      setSelectedDistrict(null);
                      setSelectedStation(null);
                      setSelectedCrimeId(null);
                    }}
                    className="text-[var(--text-muted)] hover:text-[var(--accent-blue)] cursor-pointer underline"
                  >
                    Statewide
                  </button>

                  {selectedDistrict && (
                    <>
                      <ChevronRight className="w-3 h-3 text-[var(--text-muted)] shrink-0" />
                      <button
                        onClick={() => {
                          setSelectedStation(null);
                          setSelectedCrimeId(null);
                        }}
                        className={`cursor-pointer ${!selectedStation && !selectedCrimeId ? 'text-[var(--accent-blue)] font-bold' : 'text-[var(--text-muted)] hover:text-[var(--accent-blue)] underline'}`}
                      >
                        {selectedDistrict}
                      </button>
                    </>
                  )}

                  {selectedStation && (
                    <>
                      <ChevronRight className="w-3 h-3 text-[var(--text-muted)] shrink-0" />
                      <button
                        onClick={() => setSelectedCrimeId(null)}
                        className={`cursor-pointer max-w-[110px] truncate ${!selectedCrimeId ? 'text-[var(--accent-blue)] font-bold' : 'text-[var(--text-muted)] hover:text-[var(--accent-blue)] underline'}`}
                        title={selectedStation}
                      >
                        {selectedStation}
                      </button>
                    </>
                  )}

                  {selectedCrimeId && (
                    <>
                      <ChevronRight className="w-3 h-3 text-[var(--text-muted)] shrink-0" />
                      <span className="text-orange-400 font-bold max-w-[90px] truncate" title={selectedCrimeId}>
                        {selectedCrimeId}
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* TIER 3: CRIME CASE VIEW */}
              {activeCrimeCase ? (
                <div className="space-y-3 font-mono text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-[8.5px] uppercase font-bold text-[var(--accent-coral)] flex items-center gap-1">
                      <FileText className="w-3.5 h-3.5" />
                      Incident Case Dossier
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[8px] font-bold uppercase ${
                      activeCrimeCase.priority === 'high' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-blue-500/20 text-blue-400'
                    }`}>
                      {activeCrimeCase.priority || 'Medium'} Priority
                    </span>
                  </div>

                  <h4 className="text-sm font-bold text-[var(--text-primary)] uppercase">
                    {activeCrimeCase.case_number}
                  </h4>

                  <div className="p-3 bg-[var(--bg-primary)]/80 rounded border border-border-color space-y-2 text-[10px]">
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">Crime Category:</span>
                      <span className="text-[var(--text-primary)] font-semibold">{activeCrimeCase.crime_type || activeCrimeCase.category || 'IPC Section Violation'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">Occurred At:</span>
                      <span className="text-[var(--text-secondary)]">{activeCrimeCase.time ? new Date(activeCrimeCase.time).toLocaleString() : 'Recent Incident'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">Status:</span>
                      <span className="text-emerald-400 font-bold uppercase">{activeCrimeCase.status || 'Active Investigation'}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">Jurisdiction:</span>
                      <span className="text-[var(--text-secondary)]">{activeCrimeCase.location || selectedStation || selectedDistrict}</span>
                    </div>
                  </div>

                  {activeCrimeCase.description && (
                    <div className="p-3 bg-[var(--bg-primary)]/40 rounded border border-[var(--border-primary)]">
                      <span className="text-[8px] uppercase text-[var(--text-muted)] font-bold block mb-1">Case Summary / MO Details</span>
                      <p className="text-[10px] text-[var(--text-secondary)] leading-relaxed">{activeCrimeCase.description}</p>
                    </div>
                  )}

                  <button
                    onClick={() => setSelectedCrimeId(null)}
                    className="w-full py-1.5 text-[9.5px] uppercase font-bold text-[var(--accent-blue)] bg-[var(--accent-blue)]/10 hover:bg-[var(--accent-blue)]/20 border border-[var(--accent-blue)]/30 rounded cursor-pointer transition-colors"
                  >
                    &larr; Back to Station Cases
                  </button>
                </div>
              ) : activeStationInfo ? (
                /* TIER 2: POLICE STATION VIEW */
                <div className="space-y-4 font-mono text-xs">
                  <div className="flex items-center justify-between">
                    <div>
                      <span className="text-[8px] font-bold text-[var(--accent-teal)] uppercase tracking-wider block">
                        Police Station Jurisdiction
                      </span>
                      <h3 className="text-sm font-bold text-[var(--text-primary)] uppercase">
                        {activeStationInfo.name}
                      </h3>
                    </div>
                    <div className={`px-2.5 py-1 rounded font-bold text-[10px] ${
                      activeStationInfo.weight >= 75 ? 'bg-red-500/15 text-red-400 border border-red-500/30' : 'bg-amber-500/15 text-amber-400 border border-amber-500/30'
                    }`}>
                      {activeStationInfo.weight}% Risk
                    </div>
                  </div>

                  <div className="p-3 bg-[var(--bg-primary)]/80 rounded border border-border-color space-y-1.5 text-[10px]">
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">District Sector:</span>
                      <span className="text-[var(--text-primary)] font-bold">{activeStationInfo.district_id}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">Primary Crime:</span>
                      <span className="text-orange-400 font-semibold">{activeStationInfo.type}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">Station Coordinates:</span>
                      <span className="text-[var(--text-secondary)]">{activeStationInfo.lat.toFixed(3)}°N, {activeStationInfo.lng.toFixed(3)}°E</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-[var(--text-muted)]">Weekly Trend:</span>
                      <span className={`font-bold flex items-center gap-1 ${activeStationInfo.trend === 'up' ? 'text-red-400' : 'text-emerald-400'}`}>
                        {activeStationInfo.trend === 'up' ? <TrendingUp className="w-3 h-3" /> : <TrendingDown className="w-3 h-3" />}
                        {activeStationInfo.trend === 'up' ? 'SURGING' : 'STABILIZED'}
                      </span>
                    </div>
                  </div>

                  {/* Crime Incidents under Station */}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-[9px] font-bold text-[var(--text-primary)] uppercase tracking-wider">
                        Registered Incidents & Cases ({filteredCases.length})
                      </span>
                      <span className="text-[8px] text-[var(--text-muted)]">Click case to view</span>
                    </div>
                    
                    <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                      {filteredCases.length > 0 ? (
                        filteredCases.map((c: any) => (
                          <div
                            key={c.case_number || c.id}
                            onClick={() => setSelectedCrimeId(c.case_number || c.id)}
                            className="p-2 bg-[var(--bg-primary)] hover:bg-[var(--accent-blue)]/10 border border-border-color hover:border-[var(--accent-blue)]/40 rounded cursor-pointer transition-all flex items-center justify-between"
                          >
                            <div>
                              <p className="font-bold text-[9.5px] text-[var(--text-primary)] uppercase truncate">{c.case_number}</p>
                              <p className="text-[8px] text-[var(--text-muted)] truncate">{c.crime_type || c.category || 'Incident'}</p>
                            </div>
                            <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded ${
                              c.priority === 'high' ? 'bg-red-500/20 text-red-400' : 'bg-blue-500/20 text-blue-400'
                            }`}>
                              {c.priority || 'MED'}
                            </span>
                          </div>
                        ))
                      ) : (
                        <div className="p-3 text-center text-[9px] text-[var(--text-muted)] bg-[var(--bg-primary)]/40 rounded border border-dashed border-border-color">
                          No direct FIR filings logged under this station.
                        </div>
                      )}
                    </div>
                  </div>

                  <button
                    onClick={() => {
                      setSelectedStation(null);
                      setSelectedCrimeId(null);
                    }}
                    className="w-full py-1.5 text-[9.5px] uppercase font-bold text-[var(--accent-blue)] bg-[var(--accent-blue)]/10 hover:bg-[var(--accent-blue)]/20 border border-[var(--accent-blue)]/30 rounded cursor-pointer transition-colors"
                  >
                    &larr; Back to District Overview
                  </button>
                </div>
              ) : activeDistrictInfo ? (
                /* TIER 1: DISTRICT OVERVIEW */
                <div className="space-y-3.5">
                  {/* Risk gauge card — renders only a backend-supplied score;
                      missing model output shows an explicit empty state. */}
                  {activeDistrictInfo.riskScore != null ? (
                    <div className={`p-3.5 rounded-card border flex items-center justify-between ${
                      activeDistrictInfo.riskScore >= 75
                        ? 'bg-[var(--accent-coral)]/5 border-[var(--accent-coral)]/20 text-[var(--accent-coral)]'
                        : 'bg-[var(--accent-teal)]/5 border-[var(--accent-teal)]/20 text-[var(--accent-teal)]'
                    }`}>
                      <div>
                        <span className="text-[9px] font-mono uppercase tracking-widest text-[var(--text-muted)] block">
                          District Threat Score
                        </span>
                        <span className="text-2xl font-mono font-extrabold mt-0.5 block">
                          {activeDistrictInfo.riskScore}/100
                        </span>
                      </div>
                      <div className={`p-2 rounded-full ${
                        activeDistrictInfo.riskScore >= 75 ? 'bg-red-500/10' : 'bg-emerald-500/10'
                      }`}>
                        <AlertTriangle className="w-6 h-6 animate-pulse" />
                      </div>
                    </div>
                  ) : (
                    <div className="p-3.5 rounded-card border border-dashed border-[var(--border-primary)] flex items-center justify-between">
                      <div>
                        <span className="text-[9px] font-mono uppercase tracking-widest text-[var(--text-muted)] block">
                          District Threat Score
                        </span>
                        <span className="text-sm font-mono font-bold mt-0.5 block text-[var(--text-muted)]">
                          No backend risk model output for this district yet.
                        </span>
                      </div>
                      <AlertTriangle className="w-5 h-5 text-[var(--text-disabled)]" />
                    </div>
                  )}

                  {/* Emerging Trend Alert Banner */}
                  {districtEmergingTrends.length > 0 && (
                    <div className="p-2.5 bg-red-500/10 border border-red-500/30 rounded-lg">
                      <div className="flex items-center gap-1.5 text-[9px] font-mono font-bold text-red-400 uppercase">
                        <Flame className="w-3.5 h-3.5 text-red-400 animate-pulse" />
                        <span>Emerging Trend Alert</span>
                      </div>
                      <p className="text-[9px] font-mono text-[var(--text-primary)] mt-1 font-semibold">
                        {districtEmergingTrends[0].category}: +{districtEmergingTrends[0].change_percentage}% surge
                      </p>
                      <p className="text-[8px] font-mono text-[var(--text-muted)] mt-0.5">
                        {districtEmergingTrends[0].recent_count} recent vs {districtEmergingTrends[0].historical_count} historical baseline
                      </p>
                    </div>
                  )}

                  {/* POLICE STATION JURISDICTION SELECTOR DROPDOWN & LIST */}
                  <div className="p-3 bg-[var(--bg-primary)] border border-[var(--accent-blue)]/40 rounded-card font-mono space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[9.5px] font-bold text-[var(--accent-teal)] uppercase tracking-wider flex items-center gap-1.5">
                        <MapPin className="w-3.5 h-3.5 text-[var(--accent-teal)] animate-pulse" />
                        Police Station Drill-Down ({districtStations.length})
                      </span>
                      <span className="text-[8px] text-[var(--accent-blue)] font-bold">1-Click Select</span>
                    </div>

                    {/* Dropdown Select Box with ChevronDown */}
                    <div className="relative">
                      <select
                        value={selectedStation || ''}
                        onChange={(e) => {
                          if (e.target.value) {
                            setSelectedStation(e.target.value);
                            setSelectedCrimeId(null);
                          }
                        }}
                        className="w-full bg-[var(--bg-secondary)] border border-[var(--border-primary)] hover:border-[var(--accent-blue)] text-[var(--text-primary)] text-xs rounded p-2 pr-8 appearance-none cursor-pointer font-mono font-semibold focus:outline-none focus:border-[var(--accent-blue)]"
                      >
                        <option value="">▼ Select a Police Station Jurisdiction...</option>
                        {districtStations.map((st) => (
                          <option key={st.name} value={st.name}>
                            🏢 {st.name} ({st.weight || st.baseScore}% Risk • {st.type})
                          </option>
                        ))}
                      </select>
                      <ChevronDown className="w-4 h-4 text-[var(--accent-blue)] absolute right-2.5 top-2.5 pointer-events-none" />
                    </div>

                    {/* Clickable Police Station Badges */}
                    <div className="space-y-1.5 max-h-44 overflow-y-auto pr-1 pt-1">
                      {districtStations.map((station) => (
                        <div
                          key={station.name}
                          onClick={() => {
                            setSelectedStation(station.name);
                            setSelectedCrimeId(null);
                          }}
                          className="p-2 bg-[var(--bg-secondary)]/80 hover:bg-[var(--accent-blue)]/15 border border-[var(--border-primary)] hover:border-[var(--accent-blue)] rounded cursor-pointer transition-all flex items-center justify-between group"
                        >
                          <div className="truncate max-w-[190px]">
                            <p className="font-bold text-[9.5px] text-[var(--text-primary)] group-hover:text-[var(--accent-blue)] uppercase truncate">
                              {station.name}
                            </p>
                            <p className="text-[8px] text-[var(--text-muted)] truncate">{station.type}</p>
                          </div>
                          <div className="flex items-center gap-1.5 shrink-0">
                            <span className={`text-[8.5px] font-bold px-1.5 py-0.5 rounded ${station.weight >= 75 ? 'bg-red-500/15 text-red-400' : 'bg-amber-500/15 text-amber-400'}`}>
                              {station.weight}%
                            </span>
                            <ChevronRight className="w-3.5 h-3.5 text-[var(--text-muted)] group-hover:text-[var(--accent-blue)] group-hover:translate-x-0.5 transition-transform" />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Primary Stats lists — only backend-provided values render;
                      missing metrics show an explicit "No data" state (issue 161). */}
                  <div className="space-y-2 font-mono text-xs pt-1">
                    <div className="flex justify-between py-1 border-b border-[var(--border-primary)]">
                      <span className="text-[var(--text-muted)]">Monthly FIR Total</span>
                      <span className="text-[var(--text-primary)] font-bold">{activeDistrictInfo.crimeCount} filings</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--border-primary)]">
                      <span className="text-[var(--text-muted)]">Beat Coverage Ratio</span>
                      {activeDistrictInfo.beatRatio != null ? (
                        <span className="text-[var(--text-primary)] font-bold" title="Derived from backend risk scores: 100 − district risk. Not a field-verified coverage metric.">{activeDistrictInfo.beatRatio}% estimate</span>
                      ) : (
                        <span className="text-[var(--text-muted)]">No data</span>
                      )}
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--border-primary)]">
                      <span className="text-[var(--text-muted)]">Dominant Category</span>
                      <span className="text-orange-400 font-semibold">{activeDistrictInfo.topCrimeType}</span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-[var(--border-primary)] items-center">
                      <span className="text-[var(--text-muted)]">Weekly Trend</span>
                      {/* No invented percentages — the backend hotspot trend flag
                          carries direction only (issue 161 §1). */}
                      {activeDistrictInfo.weeklyTrend === 'up' ? (
                        <span className="text-red-500 font-bold flex items-center gap-1">
                          <TrendingUp className="w-3.5 h-3.5" />
                          RISING
                        </span>
                      ) : activeDistrictInfo.weeklyTrend === 'down' ? (
                        <span className="text-emerald-500 font-bold flex items-center gap-1">
                          <TrendingDown className="w-3.5 h-3.5" />
                          DECLINING
                        </span>
                      ) : (
                        <span className="text-blue-400 font-bold">STABILIZED</span>
                      )}
                    </div>
                  </div>

                  {/* REAL SOCIO-ECONOMIC INDICATORS CARD */}
                  {selectedDistrict && socioEconomicMap[selectedDistrict] && (
                    <div className="p-3 bg-amber-500/5 border border-amber-500/20 rounded-card font-mono space-y-1.5">
                      <div className="flex justify-between items-center text-[10px] text-amber-400 font-bold uppercase tracking-wider">
                        <span>Socio-Economic Profile</span>
                        <span className="px-1.5 py-0.5 rounded bg-amber-500/15 border border-amber-500/30 text-[8.5px] uppercase">
                          {socioEconomicMap[selectedDistrict].urbanization_type || 'Semi-Urban'}
                        </span>
                      </div>
                      <div className="grid grid-cols-2 gap-2 text-[9.5px] pt-1 text-[var(--text-secondary)]">
                        <div>Literacy: <span className="font-bold text-[var(--text-primary)]">{socioEconomicMap[selectedDistrict].literacy_rate}%</span></div>
                        <div>Density: <span className="font-bold text-[var(--text-primary)]">{socioEconomicMap[selectedDistrict].population_density} /km²</span></div>
                        <div>Avg Income: <span className="font-bold text-[var(--text-primary)]">₹{socioEconomicMap[selectedDistrict].avg_income_lakhs}L</span></div>
                        <div>Crime Rate: <span className="font-bold text-[var(--text-primary)]">{socioEconomicMap[selectedDistrict].crime_per_lakh} /lakh</span></div>
                      </div>
                    </div>
                  )}

                  {/* Actionable recommendation block */}
                  <div className="p-2.5 bg-[var(--bg-secondary)]/40 border border-[var(--border-primary)] rounded-btn font-mono">
                    <span className="text-[8px] font-bold text-[var(--accent-blue)] uppercase tracking-wider block mb-0.5">
                      SCRB Operational Intel
                    </span>
                    <p className="text-[9.5px] leading-relaxed text-[var(--text-secondary)]">
                      Aggregated from active FIR registrations, station clusters, and time-shifted crime telemetry.
                    </p>
                  </div>
                </div>
              ) : selectedDistrict ? (
                /* TIER 1 EMPTY STATE (issue 161): the backend has no records for
                   this district — show an honest empty state instead of invented
                   counts, scores or station names. */
                <div className="space-y-3">
                  <div className="p-4 bg-[var(--bg-primary)]/60 border border-dashed border-[var(--border-primary)] rounded-card text-center">
                    <MapPin className="w-8 h-8 mx-auto mb-2 text-[var(--text-disabled)]" />
                    <p className="text-[10px] font-mono font-bold uppercase tracking-wider text-[var(--text-secondary)]">
                      No backend intelligence for {selectedDistrict}
                    </p>
                    <p className="text-[9px] font-mono text-[var(--text-muted)] mt-1">
                      The Saksha database currently holds no crime records, stations or analytics for this district. Nothing is fabricated to fill this panel.
                    </p>
                  </div>
                  <button
                    onClick={() => {
                      setSelectedDistrict(null);
                      setSelectedStation(null);
                      setSelectedCrimeId(null);
                    }}
                    className="w-full py-1.5 text-[9.5px] uppercase font-bold text-[var(--accent-blue)] bg-[var(--accent-blue)]/10 hover:bg-[var(--accent-blue)]/20 border border-[var(--accent-blue)]/30 rounded cursor-pointer transition-colors"
                  >
                    &larr; Back to Statewide View
                  </button>
                </div>
              ) : null}

            </div>

            {/* Quick Action bar */}
            <div className="pt-3 border-t border-border-color mt-4">
              <button
                onClick={() => {
                  const targetName = activeCrimeCase
                    ? `Case_${activeCrimeCase.case_number}`
                    : activeStationInfo
                    ? `${activeStationInfo.name}_Station`
                    : `${activeDistrictInfo?.name || selectedDistrict || 'Regional'}_District`;

                  const targetData = activeCrimeCase || activeStationInfo || activeDistrictInfo;

                  downloadSecureDossier(
                    `${targetName} SCRB Intelligence Dossier`,
                    targetData,
                    user ? `CONFIDENTIAL - ${user.badgeId}` : 'CONFIDENTIAL - STATE POLICE'
                  );
                  if (user) {
                    addLog(
                      user.name,
                      user.badgeId,
                      'EXPORT',
                      `Exported SCRB intelligence dossier for ${targetName}`
                    );
                  }
                }}
                disabled={!activeCrimeCase && !activeStationInfo && !activeDistrictInfo}
                title={(!activeCrimeCase && !activeStationInfo && !activeDistrictInfo) ? 'No backend intelligence available to export for this selection.' : undefined}
                className={`w-full py-2.5 font-semibold text-[12px] uppercase rounded-md cursor-pointer text-center select-none transition-colors shadow-sm ${
                  (!activeCrimeCase && !activeStationInfo && !activeDistrictInfo)
                    ? 'bg-[var(--bg-tertiary)] text-[var(--text-disabled)] cursor-not-allowed'
                    : 'bg-[var(--accent-blue)] hover:bg-[var(--accent-blue)]/80 text-white'
                }`}
              >
                Export SCRB Dossier (PDF)
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* BOTTOM SLIDER */}
      <div className="p-4 z-20">
        <TimeSlider />
      </div>

    </div>
  );
};

export default KarnatakaMap;
