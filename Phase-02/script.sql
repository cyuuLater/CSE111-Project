-- 1. Validate login for Brian Lee.
SELECT u_userkey, u_name
FROM users
WHERE u_email = 'brian.lee@ucm.edu' 
    AND u_password = 'pass123';


-- 2. 



-- 3. 



-- 4. Show Jason Wong's permit, which shows his name, permit number, and vehicle info.
SELECT u.u_name, v.v_plateno, v.v_maker, v.v_model, 
       pt.pt_category, p.p_issuedate, p.p_expirationdate, pt.pt_duration
FROM permit p
    JOIN permitType pt ON pt.pt_permittypekey = p.p_permittypekey
    JOIN users u ON p.p_userkey = u.u_userkey
    JOIN vehicles v ON p.p_vehicleskey = v.v_vehicleskey
WHERE u.u_name = 'Jason Wong';


-- 5. 



-- 6. 



-- 7. 



-- 8. 



-- 9. 



-- 10. 



-- 11. 



-- 12. 



-- 13. 
SELECT s_num FROM spots WHERE s_status = 1;


-- 14. 
SELECT s.s_spotskey, s.s_num, z.z_type AS zone, 
       l.l_name AS lot, s.s_latitude, s.s_longitude
FROM spots s
    JOIN zone z ON s.s_zonekey = z.z_zonekey
    JOIN lot l ON s.s_lotkey = l.l_lotkey
WHERE s.s_status = 0;   -- 0 = available, 1 = occupied


-- 15. Checks all the spots that are occupied and the information of who's parked in them
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


-- 16. Find all spots where Alice Kim can park and their corresponding zone and lot assignments. Note Green
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


-- 17. Find the users who haven't parked yet and their cooresponding vehicle plate numbers.
SELECT u.u_name, v.v_plateno
FROM users u
JOIN vehicles v ON u.u_userkey = v.v_userkey
LEFT JOIN parkingHistory ph 
    ON ph.ph_vehicleskey = v.v_vehicleskey
WHERE ph.ph_vehicleskey IS NULL
ORDER BY u.u_userkey;


-- 18. 



-- 19. 



-- 20. 
