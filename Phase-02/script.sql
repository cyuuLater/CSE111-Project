-- =====   SIMPLE/SELECT QUERIES   ===== --
-- 1. Validate login for Brian Lee.
SELECT u_userkey, u_name
FROM users
WHERE u_email = 'brian.lee@ucm.edu' 
    AND u_password = 'pass123';


-- 2. View Map (Get all lots, spots, and zone assignments).
SELECT l.l_name AS lot, z.z_type AS zone, s.s_num AS spot,
       s.s_status AS occupied, s.s_latitude AS lat, s.s_longitude AS lon
FROM spots s
    JOIN zone z ON z.z_zonekey = s.s_zonekey
    JOIN lot l ON l.l_lotkey = s.s_lotkey
ORDER BY l.l_name, 
    SUBSTR(s.s_num,1,1), -- A, B, C, D, E
    CAST(SUBSTR(s.s_num,2) AS INT); -- 1..100


-- 3. Check which users are currently not parked anywhere and their vehicle plate numbers.
SELECT u.u_name, v.v_plateno
FROM users u
JOIN vehicles v ON u.u_userkey = v.v_userkey
LEFT JOIN parkingHistory ph 
    ON ph.ph_vehicleskey = v.v_vehicleskey
WHERE ph.ph_vehicleskey IS NULL
ORDER BY u.u_userkey;


-- 4. Find the users who haven't parked yet and their cooresponding vehicle plate numbers.
SELECT u.u_name, v.v_plateno
FROM users u
JOIN vehicles v ON u.u_userkey = v.v_userkey
LEFT JOIN parkingHistory ph 
    ON ph.ph_vehicleskey = v.v_vehicleskey
WHERE ph.ph_vehicleskey IS NULL
ORDER BY u.u_userkey;


-- 5. Find which spots are available along with their corresponding zone, lot, and coordinates.
SELECT s.s_spotskey, s.s_num, z.z_type AS zone, 
       l.l_name AS lot, s.s_latitude, s.s_longitude
FROM spots s
    JOIN zone z ON s.s_zonekey = z.z_zonekey
    JOIN lot l ON s.s_lotkey = l.l_lotkey
WHERE s.s_status = 0; -- 0 = available, 1 = occupied



-- =====   INSERT/DELETE/UPDATE QUERIES   ===== --
-- 6. Insert/Create a new user.
INSERT INTO users(u_userkey, u_name, u_email, u_password)
VALUES(31, 'Jenna Moore', 'jenna.moore@ucm.edu', 'pass123');


-- 7. Have a user insert their car information.
INSERT INTO vehicles(v_vehicleskey, v_userkey, v_plateno, v_platestate, v_maker, v_model, v_color)
VALUES(31, 31, '9XKT221', 'CA', 'Toyota', 'Corolla', 'Blue');


-- 8. Have a user apply for an Off-Campus Semester permit.
INSERT INTO permit(p_permitkey, p_userkey, p_vehicleskey, p_permittypekey, p_permitnum, p_issuedate, p_expirationdate)
VALUES(31, 31, 31, 5, 'PRM031', '2025-11-20', '2025-12-23');
DELETE FROM permit
WHERE p_permitkey = 31;


-- 9. DELETE any permits passed their expiration dates.
DELETE FROM permit
WHERE p_expirationdate < '2025-11-20';


-- 10. Jenna Moore leaves from her spot. Delete that record from parking history accordingly.
DELETE FROM parkingHistory
WHERE ph_vehicleskey = 31
    AND ph_spotskey = 20
    AND ph_departuretime IS NULL;
UPDATE spots
SET s_status = 0
WHERE s_spotskey = 20;


-- 11. Jenna Moore occupies a spot.
INSERT INTO parkingHistory(ph_parkinghistkey, ph_vehicleskey, ph_spotskey, ph_arrivaltime, ph_departuretime)
VALUES(21, 31, 20, '2025-11-20', NULL);
UPDATE spots
SET s_status = 1
WHERE s_spotskey = 20;


-- 12. Let's say A60-A80 are needed for construction. Update all those spots to inactive. Can also assume users
--     left/don't park in those spots before starting construction.
UPDATE spots
SET s_isactive = 0
WHERE s_num BETWEEN 'A60' AND 'A80';



-- =====   COMPLICATED QUERIES   ===== --
-- 13.  #Dynamically Change The Status of Lot Spots Based on time of day/day of week
 -- 7pm to 6am, GOLD -> GREEN--
 -- H ->! GREEN -- 
 -- MIGHT NEED TO CREATE ATTRIBUTE FOR TIME OF DAY/ DAY OF WEEK --




-- 14. Show Jason Wong's permit, which shows his name, permit number, permit type, and vehicle info.
SELECT u.u_name, v.v_plateno, v.v_maker, v.v_model, 
       pt.pt_category, p.p_issuedate, p.p_expirationdate, pt.pt_duration
FROM permit p
    JOIN permitType pt ON pt.pt_permittypekey = p.p_permittypekey
    JOIN users u ON p.p_userkey = u.u_userkey
    JOIN vehicles v ON p.p_vehicleskey = v.v_vehicleskey
WHERE u.u_name = 'Jason Wong';


-- 15. 



-- 16. Check all the spots that are occupied and the information of who's parked in them
--     (such as their plate num, permit types, permit numbers, spots, zones, and lots).
SELECT u.u_name AS user, v.v_plateno AS plate, pt.pt_category  AS permit_type, 
       p.p_permitnum AS permit_number, s.s_num AS spot, z.z_type AS zone, l.l_name AS lot
FROM parkingHistory ph
    JOIN vehicles v ON ph.ph_vehicleskey = v.v_vehicleskey
    JOIN users u ON v.v_userkey = u.u_userkey
    JOIN permit p ON p.p_vehicleskey = v.v_vehicleskey
    JOIN permitType pt ON pt.pt_permittypekey = p.p_permittypekey
    JOIN spots s ON ph.ph_spotskey = s.s_spotskey
    JOIN zone z ON z.z_zonekey = s.s_zonekey
    JOIN lot l ON l.l_lotkey = s.s_lotkey
ORDER BY SUBSTR(s.s_num, 1, 1);


-- 17. Find all spots where Alice Kim can park and their corresponding zone and lot assignments. Note Green
--     Zone (1) allows all user types to park there. Gold Zone (2) allows only Faculty, and H Zone (3) only
--     allows On-Campus Students.
SELECT s.s_num AS spot, z.z_type AS zone, l.l_name AS lot
FROM users u
    JOIN vehicles v ON v.v_userkey = u.u_userkey
    JOIN permit p ON p.p_vehicleskey = v.v_vehicleskey
    JOIN permitType pt ON pt.pt_permittypekey = p.p_permittypekey
    JOIN spots s ON (
            (pt.pt_category = 'On-Campus Student' AND s.s_zonekey IN (1, 3)) OR
            (pt.pt_category = 'Off-Campus Student' AND s.s_zonekey = 1) OR
            (pt.pt_category = 'Guest' AND s.s_zonekey = 1) OR
            (pt.pt_category = 'Faculty' AND s.s_zonekey IN (1, 2)) 
        )
    JOIN zone z ON z.z_zonekey = s.s_zonekey
    JOIN lot l ON l.l_lotkey = s.s_lotkey
WHERE u.u_name = 'Alice Kim'
    AND s.s_status = 0 -- vacant spot
    AND s.s_isactive = 1 -- active spot
ORDER BY SUBSTR(s.s_num, 1, 1), -- A, B, C, D, E
    CAST(SUBSTR(s.s_num, 2) AS INTEGER); -- 1,2,3...


-- 18. 



-- 19. 


-- 20. 
