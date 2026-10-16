'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';

import {
  browserMapsKey,
  loadGoogleMaps,
  markerInfo,
  nearbyMarkers,
} from '@/lib/projects/project-location-map';

import type { LocationIntelligence, NearbyPlace } from './projects-detail-media-model';

type MapStatus = 'missing' | 'loading' | 'ready' | 'error';

type LatLng = { lat: number; lng: number };

type GoogleMarker = {
  setMap: (map: GoogleMap | null) => void;
  addListener: (event: string, handler: () => void) => void;
};

type GoogleMap = {
  fitBounds: (bounds: GoogleBounds, padding?: number) => void;
};

type GoogleBounds = {
  extend: (position: LatLng) => void;
};

type GoogleInfoWindow = {
  setContent: (node: HTMLElement) => void;
  open: (options: { map: GoogleMap; anchor: GoogleMarker }) => void;
};

type GoogleMapsApi = {
  maps: {
    Map: new (element: HTMLElement, options: Record<string, unknown>) => GoogleMap;
    Marker: new (options: Record<string, unknown>) => GoogleMarker;
    InfoWindow: new () => GoogleInfoWindow;
    LatLngBounds: new () => GoogleBounds;
    SymbolPath: { CIRCLE: number };
  };
};

function infoNode(name: string, category: string, address: string) {
  const root = document.createElement('div');
  const title = document.createElement('strong');
  title.textContent = name;
  root.append(title);
  const categoryLine = document.createElement('div');
  categoryLine.textContent = category;
  root.append(categoryLine);
  if (address) {
    const addressLine = document.createElement('div');
    addressLine.textContent = address;
    root.append(addressLine);
  }
  return root;
}

export function ProjectsDetailLocationMap({
  location,
  locale,
  category,
}: {
  location: LocationIntelligence;
  locale: string;
  category: string;
}) {
  const t = useTranslations('projects.detail.twin');
  const canvasRef = useRef<HTMLDivElement>(null);
  const key = browserMapsKey();
  const [status, setStatus] = useState<MapStatus>(key ? 'loading' : 'missing');
  const centerLat = location.lat;
  const centerLng = location.lng;
  const places = nearbyMarkers(location.nearbyPlaces, category) as NearbyPlace[];
  const markerKey = places.map((place) => `${place.id}:${place.lat}:${place.lng}`).join('|');
  const placesRef = useRef(places);
  const translateRef = useRef(t);
  placesRef.current = places;
  translateRef.current = t;

  useEffect(() => {
    if (!key || centerLat == null || centerLng == null) return;
    const canvas = canvasRef.current;
    if (!canvas) return;
    let cancelled = false;
    const created: GoogleMarker[] = [];
    const plotted = placesRef.current;
    setStatus('loading');
    loadGoogleMaps(key)
      .then((loaded: GoogleMapsApi) => {
        if (cancelled) return;
        const maps = loaded.maps;
        const center = { lat: centerLat, lng: centerLng };
        const map = new maps.Map(canvas, {
          center,
          zoom: 15,
          mapTypeControl: false,
          streetViewControl: false,
          fullscreenControl: true,
          clickableIcons: false,
        });
        new maps.Marker({
          map,
          position: center,
          title: translateRef.current('location.projectMarker'),
          zIndex: 1000,
        });
        const info = new maps.InfoWindow();
        const bounds = new maps.LatLngBounds();
        bounds.extend(center);
        for (const place of plotted) {
          if (place.lat == null || place.lng == null) continue;
          const position = { lat: place.lat, lng: place.lng };
          bounds.extend(position);
          const details = markerInfo(place, locale) as { name: string; category: string; address: string };
          const marker = new maps.Marker({
            map,
            position,
            title: details.name,
            zIndex: 1,
            icon: {
              path: maps.SymbolPath.CIRCLE,
              scale: 7,
              fillColor: '#58aebb',
              fillOpacity: 1,
              strokeColor: '#075b75',
              strokeWeight: 1,
            },
          });
          marker.addListener('click', () => {
            const categoryLabel = translateRef.current(`location.categories.${details.category}`);
            info.setContent(infoNode(details.name, categoryLabel, details.address));
            info.open({ map, anchor: marker });
          });
          created.push(marker);
        }
        if (plotted.length > 0) map.fitBounds(bounds, 48);
        setStatus('ready');
      })
      .catch(() => {
        if (!cancelled) setStatus('error');
      });
    return () => {
      cancelled = true;
      for (const marker of created) marker.setMap(null);
    };
  }, [centerLat, centerLng, key, locale, markerKey]);

  if (!key || status === 'missing') {
    return (
      <div
        className="proj-detail-ds__map proj-detail-ds__map-fallback"
        data-testid="project-location-map-fallback"
        role="status"
      >
        <p>{t('location.mapMissingKey')}</p>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div
        className="proj-detail-ds__map proj-detail-ds__map-fallback"
        data-testid="project-location-map-fallback"
        role="alert"
      >
        <p>{t('location.mapLoadError')}</p>
      </div>
    );
  }

  return (
    <div className="proj-detail-ds__map" data-testid="project-location-map" aria-label={t('location.mapAria')}>
      <div ref={canvasRef} className="proj-detail-ds__map-canvas" />
    </div>
  );
}
