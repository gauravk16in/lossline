import chickenBiryaniImg from '../assets/food/chicken-biryani.png';
import paneerBiryaniImg from '../assets/food/paneer-biryani.png';
import vegFriedRiceImg from '../assets/food/veg-fried-rice.png';
import masalaChaasImg from '../assets/food/masala-chaas.png';
import gulabJamunImg from '../assets/food/gulab-jamun.png';
import dalMakhaniImg from '../assets/food/dal-makhani.png';
import hakkaNoodlesImg from '../assets/food/hakka-noodles.png';
import coldCoffeeImg from '../assets/food/cold-coffee.png';

const CATALOG: Record<string, { name: string; category: string; image: string }> = {
  CHICKEN_BIRYANI: { name: 'Chicken Biryani', category: 'Main Course', image: chickenBiryaniImg },
  PANEER_BIRYANI: { name: 'Paneer Biryani', category: 'Main Course', image: paneerBiryaniImg },
  VEG_FRIED_RICE: { name: 'Veg Fried Rice', category: 'Rice', image: vegFriedRiceImg },
  MASALA_CHAAS: { name: 'Masala Chaas', category: 'Beverage', image: masalaChaasImg },
  GULAB_JAMUN: { name: 'Gulab Jamun', category: 'Dessert', image: gulabJamunImg },
  DAL_MAKHANI: { name: 'Dal Makhani', category: 'Main Course', image: dalMakhaniImg },
  HAKKA_NOODLES: { name: 'Hakka Noodles', category: 'Sides', image: hakkaNoodlesImg },
  COLD_COFFEE: { name: 'Cold Coffee', category: 'Beverage', image: coldCoffeeImg },
};

export function skuDisplay(skuId: string) {
  return CATALOG[skuId] ?? {
    name: skuId.split(/[-_]/).map((part) => part.charAt(0).toUpperCase() + part.slice(1)).join(' '),
    category: 'Menu Item',
    image: vegFriedRiceImg,
  };
}
