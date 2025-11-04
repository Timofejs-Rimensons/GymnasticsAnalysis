// components/Header/HeaderBastion.jsx
import React from 'react';
import styles from './Header.module.css';

function Header() {
    return (
        <header className={styles.header}>
            <div className={styles.headerContainer}>
                {/* Логотип */}
                <a 
                    href="#about" 
                    className={styles.logo}
                    onClick={(e) => handleNavClick(e, '#about')}
                >
                    <div className={styles.logoIcon}>PAT</div>
                    GymnasticsAnalysis
                </a>
            </div>
        </header>
    );
}


export default Header;