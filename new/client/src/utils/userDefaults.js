/**
 * Utility functions to resolve and match default operational parameters
 * (Region, Division, Activity, Facility) for connected users and superusers.
 */

export const UNRESTRICTED_LOCATIONS = new Set(['all', 'global', '', 'none', 'null', 'undefined']);

export function isUnrestrictedLocation(loc) {
  if (loc === null || loc === undefined) return true;
  return UNRESTRICTED_LOCATIONS.has(String(loc).trim().toLowerCase());
}

/**
 * Normalizes activity names and checks if two activity values correspond to the same sector.
 * Handles abbreviations (EP, RPC, TRC, LQS) and descriptive names (Upstream, Downstream, etc.).
 */
export function matchesActivity(act1, act2) {
  if (!act1 || !act2) return false;
  const a = String(act1).trim().toLowerCase();
  const b = String(act2).trim().toLowerCase();
  if (a === b) return true;

  const upstreamAliases = ['ep', 'upstream', 'exploration & production', 'exploration and production', 'upstream oil & gas'];
  const downstreamAliases = ['rpc', 'downstream', 'refining and petrochemicals', 'refining & petrochemicals', 'raffinage', 'petrochimie'];
  const midstreamAliases = ['trc', 'midstream', 'transport (trc)', 'transport'];
  const lqsAliases = ['lqs', 'liquifaction and separation', 'lng', 'lpg'];

  if (upstreamAliases.includes(a) && upstreamAliases.includes(b)) return true;
  if (downstreamAliases.includes(a) && downstreamAliases.includes(b)) return true;
  if (midstreamAliases.includes(a) && midstreamAliases.includes(b)) return true;
  if (lqsAliases.includes(a) && lqsAliases.includes(b)) return true;

  return false;
}

/**
 * Checks if a facility matches a given region identifier (checking region, location, name, code).
 */
export function matchesFacilityRegion(facility, regionStr) {
  if (!facility || !regionStr) return false;
  const target = String(regionStr).trim().toLowerCase();
  if (target === 'all' || target === '') return true;

  const fReg = (facility.region || '').trim().toLowerCase();
  const fLoc = (facility.location || '').trim().toLowerCase();
  const fName = (facility.name || '').trim().toLowerCase();
  const fCode = (facility.code || '').trim().toLowerCase();

  return (
    fReg === target ||
    fLoc === target ||
    fName === target ||
    fCode === target ||
    fReg.includes(target) ||
    fLoc.includes(target) ||
    fName.includes(target)
  );
}

/**
 * Returns default region, division, activity, and facility for a connected user/superuser.
 * 
 * @param {object} user - The connected user object from AuthContext
 * @param {Array} facilities - The list of accessible facilities
 * @returns {object} { defaultRegion, defaultDivision, defaultActivity, defaultFacilityId, defaultFacilityName, isRestricted }
 */
export function getUserOperationalDefaults(user, facilities = []) {
  const defaults = {
    defaultRegion: '',
    defaultDivision: '',
    defaultActivity: '',
    defaultFacilityId: '',
    defaultFacilityName: '',
    isRestricted: false,
  };

  if (!user) return defaults;

  const userLocation = (user.location || '').trim();
  const isUnrestricted = isUnrestrictedLocation(userLocation) && user.role === 'admin';
  defaults.isRestricted = !isUnrestricted;

  // 1. Direct backend-resolved defaults if provided
  if (user.default_region) defaults.defaultRegion = user.default_region;
  if (user.default_division) defaults.defaultDivision = user.default_division;
  if (user.default_activity) defaults.defaultActivity = user.default_activity;
  if (user.default_facility_id) defaults.defaultFacilityId = String(user.default_facility_id);
  if (user.default_facility_name) defaults.defaultFacilityName = user.default_facility_name;

  // 2. Resolve matching facility from facilities list
  let matchingFacility = null;
  if (facilities && facilities.length > 0) {
    if (userLocation && !isUnrestrictedLocation(userLocation)) {
      matchingFacility = facilities.find((f) => matchesFacilityRegion(f, userLocation));
    }
    // Fallback: if user has only 1 facility accessible, use it
    if (!matchingFacility && facilities.length === 1) {
      matchingFacility = facilities[0];
    }
  }

  // 3. Fallbacks and cross-resolution
  if (matchingFacility) {
    if (!defaults.defaultRegion) {
      defaults.defaultRegion = matchingFacility.region || matchingFacility.location || matchingFacility.name || userLocation;
    }
    if (!defaults.defaultFacilityId) {
      defaults.defaultFacilityId = String(matchingFacility.id);
    }
    if (!defaults.defaultFacilityName) {
      defaults.defaultFacilityName = matchingFacility.name;
    }
    if (!defaults.defaultActivity) {
      defaults.defaultActivity = matchingFacility.activity || '';
    }
    if (!defaults.defaultDivision) {
      defaults.defaultDivision = matchingFacility.division || '';
    }
  } else if (userLocation && !isUnrestrictedLocation(userLocation) && !defaults.defaultRegion) {
    defaults.defaultRegion = userLocation;
  }

  // 4. If all accessible facilities share the same region/division/activity, use that
  if (facilities && facilities.length > 0) {
    if (!defaults.defaultRegion) {
      const uniqueRegions = [...new Set(facilities.map(f => f.region || f.location).filter(Boolean))];
      if (uniqueRegions.length === 1) defaults.defaultRegion = uniqueRegions[0];
    }
    if (!defaults.defaultActivity) {
      const uniqueActivities = [...new Set(facilities.map(f => f.activity).filter(Boolean))];
      if (uniqueActivities.length === 1) defaults.defaultActivity = uniqueActivities[0];
    }
    if (!defaults.defaultDivision) {
      const uniqueDivisions = [...new Set(facilities.map(f => f.division).filter(Boolean))];
      if (uniqueDivisions.length === 1) defaults.defaultDivision = uniqueDivisions[0];
    }
    if (!defaults.defaultFacilityId && facilities.length === 1) {
      defaults.defaultFacilityId = String(facilities[0].id);
      defaults.defaultFacilityName = facilities[0].name;
    }
  }

  return defaults;
}
