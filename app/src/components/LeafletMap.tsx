import { useEffect, useMemo, useRef } from 'react';
import { WebView, WebViewMessageEvent } from 'react-native-webview';
import { colors } from '../theme';
import type { FieldCollection } from '../types';

/**
 * Satellite map with field outlines. Leaflet in a WebView: no API key,
 * works in Expo Go and in an APK.
 */
export function LeafletMap({ fields, selectedId, onSelect }: { fields: FieldCollection; selectedId?: string; onSelect: (id: string) => void }) {
  const ref = useRef<{ injectJavaScript: (js: string) => void } | null>(null);
  const key = JSON.stringify(fields.features.map((f) => [f.properties.id, f.properties.health, f.properties.weakSquares?.length ?? 0]));

  const html = useMemo(() => `<!doctype html><html><head><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>html,body,#m{margin:0;height:100%;background:${colors.sand}}
.lbl{background:${colors.paper};border:0;border-radius:999px;padding:3px 10px;font:600 13px sans-serif;color:${colors.ink};white-space:nowrap;box-shadow:0 1px 3px rgba(0,0,0,.25)}
.lbl.sel{background:${colors.green};color:${colors.paper}}
.leaflet-tooltip:before{display:none}</style></head>
<body><div id="m"></div><script>
var fields=${JSON.stringify(fields)}, sel='';
var map=L.map('m',{zoomControl:false});
L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',{maxZoom:19,attribution:'Esri'}).addTo(map);
var byId={};
function style(f){var s=f.properties.id===sel, h=f.properties.health;
  return{color:'#fff',weight:s?4:2,fillColor:h==='good'?'${colors.green}':h==='unknown'?'#ffffff':'${colors.orange}',fillOpacity:h==='unknown'?(s?0.3:0.12):(s?0.5:0.3)}}
var g=L.geoJSON(fields,{style:style,onEachFeature:function(f,l){byId[f.properties.id]=l;
  l.bindTooltip(f.properties.name,{permanent:true,direction:'center',className:'lbl'});
  l.on('click',function(){window.ReactNativeWebView.postMessage(f.properties.id)});}}).addTo(map);
map.fitBounds(g.getBounds(),{padding:[28,28]});
// 10 m squares that are often less green than the rest of their field
fields.features.forEach(function(f){(f.properties.weakSquares||[]).forEach(function(p){
  var dy=5/110574, dx=5/(111320*Math.cos(p[1]*Math.PI/180));
  L.rectangle([[p[1]-dy,p[0]-dx],[p[1]+dy,p[0]+dx]],{stroke:false,fillColor:'${colors.red}',fillOpacity:0.9,interactive:false}).addTo(map);});});
window.focusField=function(id){sel=id;g.setStyle(style);
  Object.keys(byId).forEach(function(k){var t=byId[k].getTooltip();if(t&&t.getElement())t.getElement().classList.toggle('sel',k===id);});
  var l=byId[id];if(l)map.fitBounds(l.getBounds(),{padding:[70,70],maxZoom:16});else map.fitBounds(g.getBounds(),{padding:[28,28]});};
</script></body></html>`,
  // eslint-disable-next-line react-hooks/exhaustive-deps
  [key]);

  const focus = () => ref.current?.injectJavaScript(`window.focusField && window.focusField(${JSON.stringify(selectedId ?? '')}); true;`);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(focus, [selectedId]);

  return (
    <WebView
      ref={ref as never}
      originWhitelist={['*']}
      source={{ html }}
      onMessage={(e: WebViewMessageEvent) => onSelect(e.nativeEvent.data)}
      onLoadEnd={() => { if (selectedId) focus(); }}
      style={{ flex: 1, backgroundColor: colors.sand }}
    />
  );
}
