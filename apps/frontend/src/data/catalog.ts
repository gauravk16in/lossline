import chickenBiryaniImg from '../assets/food/chicken-biryani.png';
import paneerBiryaniImg from '../assets/food/paneer-biryani.png';
import vegFriedRiceImg from '../assets/food/veg-fried-rice.png';

const CATALOG: Record<string, { name: string; category: string; image: string }> = {
  chicken_biryani: { name: 'Chicken Biryani', category: 'Main Course', image: chickenBiryaniImg },
  paneer_biryani: { name: 'Paneer Biryani', category: 'Main Course', image: paneerBiryaniImg },
  veg_fried_rice: { name: 'Veg Fried Rice', category: 'Rice', image: vegFriedRiceImg },
};

export function skuDisplay(skuId: string) {
  return CATALOG[skuId] ?? {
    name: skuId.split(/[-_]/).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' '),
    category: 'Menu Item',
    image: vegFriedRiceImg,
  };
}
