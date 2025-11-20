-- =====   SELECT QUERIES   ===== --
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
ORDER BY SUBSTR(s.s_num,1,1), -- A, B, C, D, E
    CAST(SUBSTR(s.s_num,2) AS INT); -- 1, 2, 3, ...


-- 3. Check which users are currently not parked anywhere and their vehicle plate numbers.
SELECT u.u_name, v.v_plateno
FROM users u
JOIN vehicles v ON u.u_userkey = v.v_userkey
LEFT JOIN parkingHistory ph 
    ON ph.ph_vehicleskey = v.v_vehicleskey
WHERE ph.ph_vehicleskey IS NULL
ORDER BY u.u_userkey;


-- 4. Find which spots are available along with their corresponding zone, lot, and coordinates.
SELECT s.s_spotskey, s.s_num, z.z_type AS zone, 
       l.l_name AS lot, s.s_latitude, s.s_longitude
FROM spots s
    JOIN zone z ON s.s_zonekey = z.z_zonekey
    JOIN lot l ON s.s_lotkey = l.l_lotkey
WHERE s.s_status = 0; -- 0 = available, 1 = occupied


-- 5. Show how many spots left are available in each lot.
SELECT l.l_name, (
    SELECT COUNT(*) 
    FROM spots s 
    WHERE s.s_lotkey = l.l_lotkey
        AND s.s_status = 0
    ) AS available_spots
FROM lot l;


-- 6. Show which lots are less than 30% full.
SELECT l.l_name, stats.occupied, stats.capacity
FROM lot l
JOIN (
    SELECT s_lotkey, SUM(s_status) AS occupied, COUNT(*) AS capacity
    FROM spots
    GROUP BY s_lotkey
) AS stats
ON stats.s_lotkey = l.l_lotkey
WHERE (occupied * 1.0 / capacity) <= 0.3;


-- 7. Find users and vehicles whose permits expire between today and when the semester ends.
SELECT u.u_name, v.v_plateno, p.p_permitnum, p.p_expirationdate
FROM users u
    JOIN vehicles v ON u.u_userkey = v.v_userkey
    JOIN permit p ON p.p_vehicleskey = v.v_vehicleskey
WHERE p.p_expirationdate 
    BETWEEN '2025-11-20' AND '2025-12-30';



-- =====   INSERT/DELETE/UPDATE QUERIES   ===== --
-- 8. Insert/Create a new user (Jenna Moore).
INSERT INTO users(u_userkey, u_name, u_email, u_password)
VALUES(31, 'Jenna Moore', 'jenna.moore@ucm.edu', 'pass123');


-- 9. Have Jenna Moore insert their car information.
INSERT INTO vehicles(v_vehicleskey, v_userkey, v_plateno, v_platestate, v_maker, v_model, v_color)
VALUES(31, 31, '9XKT221', 'CA', 'Toyota', 'Corolla', 'Blue');


-- 10. Have Jenna Moore apply for an Off-Campus Semester permit.
INSERT INTO permit(p_permitkey, p_userkey, p_vehicleskey, p_permittypekey, p_permitnum, p_issuedate, p_expirationdate)
VALUES(31, 31, 31, 5, 'PRM031', '2025-11-20', '2025-12-23');


-- 11. DELETE any permits passed their expiration dates.
INSERT INTO permit(p_permitkey, p_userkey, p_vehicleskey, p_permittypekey, p_permitnum, p_issuedate, p_expirationdate)
VALUES(999, 32, 32, 5, 'PRM999', '2025-01-01', '2025-01-02');
DELETE FROM permit
WHERE p_expirationdate < '2025-11-20';


-- 12. Jenna Moore occupies a spot.
INSERT INTO parkingHistory(ph_parkinghistkey, ph_vehicleskey, ph_spotskey, ph_arrivaltime, ph_departuretime)
VALUES(21, 31, 20, '2025-11-20 ' || strftime('%H:%M:%S', 'now', '-08:00'), NULL);
UPDATE spots
SET s_status = 1
WHERE s_spotskey = 20;


-- 13. Jenna Moore leaves from her spot. Delete that record from parking history accordingly and update the spot status.
DELETE FROM parkingHistory
WHERE ph_vehicleskey = 31
    AND ph_spotskey = 20
    AND ph_departuretime IS NULL;
UPDATE spots
SET s_status = 0
WHERE s_spotskey = 20;


-- 14. Let's say A60-A80 are needed for construction. Update all those spots to inactive. Can also assume users
--     left/don't park in those spots before starting construction.
UPDATE spots
SET s_isactive = 0
WHERE s_num BETWEEN 'A60' AND 'A80';


-- 15. Any user can claim spots in North Bowl if it's 'nighttime' (in this case, those spots become green zones) and the zone
--     assignment for this will be changed from gold to green.
UPDATE spots
SET s_zonekey = 1 -- Green
WHERE (s_num LIKE 'E%') 
    AND (CAST(strftime('%H', 'now', '-08:00') AS INTEGER) >= 19 
        OR CAST(strftime('%H', 'now', '-08:00') AS INTEGER) < 6);
UPDATE zoneAssignment
SET za_zonekey = 1 -- Green
WHERE za_lotkey = 3  -- North Bowl
    AND za_zonekey = 2
    AND (CAST(strftime('%H', 'now', '-08:00') AS INTEGER) >= 19
        OR CAST(strftime('%H', 'now', '-08:00') AS INTEGER) < 6);

-- 16. During 'daytime', spots North Bowl is now reserved for only faculty. Change those spots from green to gold and update the
--     zone assignment accordingly
UPDATE spots
SET s_zonekey = 2 -- Gold
WHERE (s_num LIKE 'E%') 
    AND (CAST(strftime('%H', 'now', '-08:00') AS INTEGER) >= 6
        AND CAST(strftime('%H', 'now', '-08:00') AS INTEGER) < 19);
UPDATE zoneAssignment
SET za_zonekey = 2 -- Gold
WHERE za_lotkey = 3  -- North Bowl
    AND za_zonekey = 1
    AND (CAST(strftime('%H', 'now', '-08:00') AS INTEGER) >= 6
        AND CAST(strftime('%H', 'now', '-08:00') AS INTEGER) < 19);

-- 17. Reset no matter what time it is (for demo purposes)
UPDATE spots
SET s_zonekey = 2
WHERE s_num LIKE 'E%';
UPDATE zoneAssignment
SET za_zonekey = 2 -- Gold
WHERE za_lotkey = 3  -- North Bowl
    AND za_zonekey = 1;


-- =====   COMPLICATED QUERIES   ===== --
-- 18. Show Jason Wong's permit, which shows his name, permit number, permit type, and vehicle info.
SELECT u.u_name, v.v_plateno, v.v_maker, v.v_model, 
       pt.pt_category, p.p_issuedate, p.p_expirationdate, pt.pt_duration
FROM permit p
    JOIN permitType pt ON pt.pt_permittypekey = p.p_permittypekey
    JOIN users u ON p.p_userkey = u.u_userkey
    JOIN vehicles v ON p.p_vehicleskey = v.v_vehicleskey
WHERE u.u_name = 'Jason Wong';


-- 19. Check all the spots that are occupied and the information of who's parked in them
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


-- 20. Find all spots where Alice Kim can park and their corresponding zone and lot assignments. Note Green
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
    CAST(SUBSTR(s.s_num, 2) AS INTEGER); -- 1, 2, 3...


-- 21. Show which users are allowed to park in spot E88.
SELECT u.u_name, pt.pt_category AS permit_type, s.s_num AS spot, z.z_type AS zone
FROM spots s
    JOIN zone z ON z.z_zonekey = s.s_zonekey
    JOIN permitType pt ON (
        (pt.pt_category = 'On-Campus Student' AND s.s_zonekey IN (1, 3)) OR
        (pt.pt_category = 'Off-Campus Student' AND s.s_zonekey = 1) OR
        (pt.pt_category = 'Guest' AND s.s_zonekey = 1) OR
        (pt.pt_category = 'Faculty' AND s.s_zonekey IN (1, 2))
    )
    JOIN permit p ON p.p_permittypekey = pt.pt_permittypekey
    JOIN vehicles v ON v.v_vehicleskey = p.p_vehicleskey
    JOIN users u ON u.u_userkey = v.v_userkey
WHERE s.s_num = 'E88'
ORDER BY u.u_name;


-- 22. Show which spot Ryan Patel is parked in (along with the lot info, zone info, and coordinates).
SELECT s.s_num AS spot, l.l_name AS lot, z.z_type AS zone, s.s_latitude, s.s_longitude
FROM users u
    JOIN vehicles v ON u.u_userkey = v.v_userkey
    JOIN parkingHistory ph ON v.v_vehicleskey = ph.ph_vehicleskey
    JOIN spots s ON ph.ph_spotskey = s.s_spotskey
    JOIN zone z ON s.s_zonekey = z.z_zonekey
    JOIN lot l ON s.s_lotkey = l.l_lotkey
WHERE u.u_name = 'Ryan Patel';


-- 23. Check how many spots are available in each zone per lot.
SELECT l.l_name AS lot, z.z_type AS zone, COUNT(s.s_spotskey) AS available_spots
FROM spots s
    JOIN lot l ON s.s_lotkey = l.l_lotkey
    JOIN zone z ON s.s_zonekey = z.z_zonekey
    JOIN zoneAssignment za ON za.za_zonekey = z.z_zonekey
        AND za.za_lotkey = l.l_lotkey
WHERE s.s_status = 0
    AND s.s_isactive = 1
    AND za.za_isactive = 1
GROUP BY l.l_name, z.z_type;