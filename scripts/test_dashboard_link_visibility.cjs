const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const template = fs.readFileSync(process.argv[2] || path.join(__dirname, '../templates/includes/dashboard_return.html'), 'utf8');
const script = template.match(/<script>([\s\S]*?)<\/script>/)[1].replaceAll("{% url 'tenant_dashboard' %}", '/tenant-dashboard/');
const origin = 'https://bowlinglegacy.com';
const makeLink = (href, extra = {}) => ({href: new URL(href, origin).href, hidden: false, dataset: {}, closest: () => false, ...extra});
const links = [
  makeLink('/tenant-dashboard/?resident=49'),
  makeLink('/tenant-dashboard/'),
  makeLink('/landlord-dashboard/'),
  makeLink('/superadmin-dashboard/', {closest: () => true}),
  makeLink('https://example.com/tenant-dashboard/'),
  makeLink('/tenant-dashboard/', {dataset: {keepDashboardLink: ''}}),
];
vm.runInNewContext(script, {URL, Set, window: {location: {origin}}, document: {
  addEventListener: (_, callback) => callback(),
  getElementById: () => ({textContent: JSON.stringify(['/tenant-dashboard/', '/landlord-dashboard/', '/superadmin-dashboard/'])}),
  querySelectorAll: () => links,
}});
assert.equal(links[0].hidden, false, 'Resident inspection action must remain visible');
assert.equal(links[1].hidden, true, 'Duplicate dashboard return is hidden');
assert.equal(links[2].hidden, true, 'Duplicate landlord return is hidden');
assert.equal(links[3].hidden, false, 'Primary return remains visible');
assert.equal(links[4].hidden, false, 'External link remains visible');
assert.equal(links[5].hidden, false, 'Explicitly retained link remains visible');
console.log('All six dashboard link visibility checks passed.');
