function i(e){return typeof e=="number"?new Intl.NumberFormat("de-DE").format(e):"0"}function m(e){const n=Object.entries(e);return n.length===0?"Keine Daten":n.slice(0,6).map(([t,r])=>`${t}: ${String(r)}`).join(`
`)}export{i as f,m as s};
