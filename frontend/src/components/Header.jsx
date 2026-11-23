import React, { useEffect, useRef, useState } from 'react';
import { CiMenuKebab } from 'react-icons/ci';
import Sidebar from '../utils/Sidebar';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

const Header = () => {

  const navigate = useNavigate();
  const [openSidebar, setOpenSidebar] = useState(false);
  const menuRef = useRef(null);

  const {isAuthenticated , logout} = useAuth();

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setOpenSidebar(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [])

  return (
    <>
      <div
        ref={menuRef}
        className="sm:static fixed z-100"
      >
        <div className="absolute flex items-center gap-2 m-4 bg-[#14251a] rounded-full">
          <CiMenuKebab
            className="h-10 w-10 text-3xl p-2.5 rounded-full cursor-pointer hover:bg-[#19462a] fill-white"
            onClick={() => setOpenSidebar(!openSidebar)}
          />
          <span className="h-10 flex items-center title-font text-xl select-none pr-8">
            Sage
          </span>
        </div>
        {!isAuthenticated ? <div className='absolute right-0 h-10 md:flex items-center hover:bg-[#19462a] text-md select-none rounded-full px-6 m-4 hidden bg-[#14251a] cursor-pointer'
        onClick={()=>navigate('/auth/login')}
        >
            Sign Up
        </div> 
        :
          <div className='absolute right-0 h-10 md:flex items-center text-md select-none rounded-full px-6 m-4 hidden text-red-500 bg-red-500/20 hover:bg-red-500/30 cursor-pointer'
          onClick={logout}
        >
          Sign Out
        </div>
        }
        {openSidebar && <Sidebar setOpenSidebar={setOpenSidebar} />}
      </div>

    </>
  );
};

export default Header;