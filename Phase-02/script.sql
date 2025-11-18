-- 1. 



-- 2. 



-- 3. 



-- 4. 



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
--     (such as their plate num, permit types, permit numbers, spots, zones, and lots)
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
ORDER BY s.s_spotskey;


-- 16. 
SELECT s.s_num AS spot, z.z_type AS zone, l.l_name AS lot
FROM users u
    JOIN vehicles v ON v.v_userkey = u.u_userkey
    JOIN permit p ON p.p_vehicleskey = v.v_vehicleskey
    JOIN permitType pt ON pt.pt_permittypekey = p.p_permittypekey
    JOIN spots s ON s.s_zonekey = (
            CASE 
                WHEN pt.pt_permittypekey = 6 THEN 1   -- Off-Campus Student → Green Zone
            END
        )
    JOIN zone z ON z.z_zonekey = s.s_zonekey
    JOIN lot l ON l.l_lotkey = s.s_lotkey
WHERE u.u_name = 'Daisy Nguyen'
    AND s.s_status = 0 -- available
    AND s.s_isactive = 1
ORDER BY s.s_num;


-- 17. 



-- 18. 



-- 19. 



-- 20. 
